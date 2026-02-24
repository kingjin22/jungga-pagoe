"""
APScheduler 백그라운드 자동 작업
- 매 10분  : 쿠팡 딜 sync + 가격 검증
- 매 1시간 : 네이버 딜 sync
- 매 1시간 : 가격 검증 (등록된 딜 현재 가격 체크 → 가격 오르면 자동 비활성)
"""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _sync_coupang():
    # 쿠팡 파트너스 API 승인 전까지 비활성화
    # 샘플 데이터(link.coupang.com/sample)는 이미지 없고 링크 불통 → 사용자 경험 최악
    # 파트너스 승인 후 partners.coupang.com에서 API 키 받아 활성화
    logger.info("⏸ 쿠팡 sync 비활성화 (파트너스 승인 대기 중)")
    return


async def _sync_naver():
    try:
        import app.db_supabase as db
        from app.services.naver import collect_real_deals
        from app.services.deal_validator import validator
        deals_data = await collect_real_deals(limit_per_keyword=5)
        created = skipped = 0
        for item in deals_data:
            if db.deal_url_exists(item["product_url"]):
                continue
            v = validator.validate_sync(item)
            if not v:
                logger.debug(f"[네이버skip] {v.reason}")
                skipped += 1
                continue
            # 제목+가격 중복 체크 (URL 달라도 동일 제품 방지)
            if db.deal_duplicate_exists(item["title"], v.sale_price):
                skipped += 1
                continue
            db.create_deal({
                "title": item["title"],
                "original_price": v.original_price,
                "sale_price": v.sale_price,
                "discount_rate": v.discount_rate,
                "image_url": item.get("image_url"),
                "product_url": item["product_url"],
                "source": "naver",
                "category": item.get("category", "기타"),
                "status": "active",
                "is_hot": v.is_hot,
            })
            created += 1
        logger.info(f"✅ 네이버 sync: {created}개 저장 | {skipped}개 제외")
    except Exception as e:
        logger.error(f"❌ 네이버 sync: {e}")


async def _sync_ppomppu():
    """
    뽐뿌 핫딜 수집 — Playwright 실시간 가격 검증

    파이프라인:
    1. RSS 파싱 → 제목/가격/ppomppu 포스트 URL
    2. 각 포스트 Playwright 렌더링 → 실제 쇼핑몰 URL 추출
    3. 실제 쇼핑몰 현재가 크롤링
    4. 커뮤니티 제시가 vs 실제가 비교 (±10%) → 불일치면 스킵
    5. 통과한 딜만 실제 쇼핑몰 URL로 저장
    """
    try:
        import app.db_supabase as db
        from app.services.ppomppu import fetch_ppomppu_deals
        from app.services.price_scrapers.playwright_scraper import (
            fetch_retailer_url_from_ppomppu, get_actual_price
        )
        from playwright.async_api import async_playwright

        deals_data = await fetch_ppomppu_deals()
        created = skipped = 0
        PRICE_TOLERANCE = 0.10  # 10% 오차 허용

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                      "--disable-blink-features=AutomationControlled"],
            )
            ctx = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                ),
                locale="ko-KR",
                viewport={"width": 1280, "height": 800},
            )
            page = await ctx.new_page()
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )

            for item in deals_data:
                sale = float(item.get("sale_price") or 0)
                is_free = sale == 0
                # fetch_ppomppu_deals()는 "source_post_url" 키로 뽐뿌 URL 반환
                ppomppu_url = item.get("source_post_url") or item.get("ppomppu_url") or ""

                # 이미 수집된 포스트 스킵
                if ppomppu_url and db.deal_url_exists(ppomppu_url):
                    skipped += 1
                    continue

                # ── 무료딜 (가격 검증 불필요) ─────────────────
                if is_free and ppomppu_url:
                    if not db.deal_url_exists(ppomppu_url):
                        db.create_deal({
                            "title": item["title"],
                            "original_price": 0,
                            "sale_price": 0,
                            "discount_rate": 100,
                            "image_url": item.get("image_url"),
                            "product_url": ppomppu_url,
                            "source": "community",
                            "category": item.get("category", "기타"),
                            "status": "active",
                            "is_hot": False,
                            "submitter_name": item.get("submitter_name", "뽐뿌"),
                        })
                        created += 1
                    continue

                if sale <= 0 or not ppomppu_url:
                    skipped += 1
                    continue

                # ── 실제 쇼핑몰 URL 추출 ──────────────────────
                from app.services.price_scrapers.playwright_scraper import PPOMPPU_ENDED_SENTINEL
                retailer_url = await fetch_retailer_url_from_ppomppu(ppomppu_url, playwright_page=page)
                if retailer_url == PPOMPPU_ENDED_SENTINEL:
                    logger.info(f"[뽐뿌품절] 종결된 게시물 스킵: {item['title'][:40]}")
                    skipped += 1
                    continue
                if not retailer_url:
                    logger.debug(f"[뽐뿌skip] 쇼핑몰 URL 없음: {item['title'][:40]}")
                    skipped += 1
                    continue

                if db.deal_url_exists(retailer_url):
                    skipped += 1
                    continue

                # ── 실제 현재가 크롤링 ────────────────────────
                actual = await get_actual_price(retailer_url, playwright_page=page)

                if actual is None:
                    # 크롤링 실패 → 수집 스킵 (신뢰 불가)
                    logger.debug(f"[뽐뿌skip] 가격 크롤링 실패: {item['title'][:40]}")
                    skipped += 1
                    continue

                if not actual.in_stock:
                    logger.debug(f"[뽐뿌skip] 품절: {item['title'][:40]}")
                    skipped += 1
                    continue

                # ── 가격 일치 검증 ────────────────────────────
                price_diff = abs(actual.price - sale) / sale
                if price_diff > PRICE_TOLERANCE:
                    logger.info(
                        f"[뽐뿌skip] 가격 불일치: 제시={sale:,.0f} 실제={actual.price:,.0f} "
                        f"({price_diff*100:.0f}%) | {item['title'][:35]}"
                    )
                    skipped += 1
                    continue

                # ── 중복 체크 ─────────────────────────────────
                if db.deal_duplicate_exists(item["title"], sale):
                    skipped += 1
                    continue

                # ── 할인율 계산 (실제가 기준) ──────────────────
                orig = float(item.get("original_price") or 0)
                if orig <= 0 or orig <= sale:
                    skipped += 1
                    continue
                discount_rate = round((1 - sale / orig) * 100, 1)
                if discount_rate < 10:
                    skipped += 1
                    continue

                db.create_deal({
                    "title": item["title"],
                    "description": item.get("description"),
                    "original_price": orig,
                    "sale_price": sale,
                    "discount_rate": discount_rate,
                    "image_url": item.get("image_url"),
                    "product_url": retailer_url,           # 실제 쇼핑몰 URL
                    "source_post_url": item.get("source_post_url") or ppomppu_url,  # 원글 URL (만료 감지)
                    "source": "community",
                    "category": item.get("category", "기타"),
                    "status": "active",
                    "is_hot": discount_rate >= 20,
                    "submitter_name": item.get("submitter_name", "뽐뿌"),
                    "admin_note": f"실제가 검증: {actual.price:,}원 ({actual.retailer})",
                })
                logger.info(
                    f"  ✅ 저장: {item['title'][:35]} | -{discount_rate}% | "
                    f"실제가={actual.price:,}원"
                )
                created += 1

            await browser.close()

        logger.info(f"✅ 뽐뿌 sync: {created}개 저장 | {skipped}개 제외")
    except Exception as e:
        logger.error(f"❌ 뽐뿌 sync: {e}")


async def _sync_naver_cafe():
    # ⛔ 영구 비활성화 — 커뮤니티 딜 신뢰성 문제
    logger.info("⛔ 정가거부 카페 sync 비활성화")
    return
    try:
        import app.db_supabase as db
        from app.services.naver_cafe import fetch_naver_cafe_deals

        deals_data = await fetch_naver_cafe_deals()
        created = skipped = 0

        from app.services.price_scrapers import check_community_deal_price
        from app.config import settings

        async with __import__("httpx").AsyncClient(timeout=8) as client:
            for item in deals_data:
                if db.deal_url_exists(item.get("product_url", "")):
                    skipped += 1
                    continue
                if db.deal_duplicate_exists(item["title"], item.get("sale_price", 0)):
                    skipped += 1
                    continue

                # naver_cafe는 이미 naver 검색 완료 → 딜 소진 여부만 재확인
                price_check = await check_community_deal_price(
                    title=item["title"],
                    community_price=float(item.get("sale_price") or 0),
                    naver_client_id=settings.NAVER_CLIENT_ID,
                    naver_client_secret=settings.NAVER_CLIENT_SECRET,
                    client=client,
                )
                if not price_check:
                    logger.debug(f"[카페skip] {price_check.reason} | {item['title'][:40]}")
                    skipped += 1
                    continue

                db.create_deal({
                    "title": item["title"],
                    "description": item.get("description"),
                    "original_price": price_check.naver_hprice or price_check.naver_lprice,
                    "sale_price": price_check.community_price,
                    "discount_rate": price_check.discount_vs_hprice,
                    "image_url": item.get("image_url") or price_check.image_url,
                    "product_url": price_check.naver_product_url or item.get("product_url"),
                    "source": "community",
                    "category": item.get("category", "기타"),
                    "status": "active",
                    "is_hot": price_check.discount_vs_hprice >= 20,
                    "submitter_name": item.get("submitter_name", "정가거부"),
                    "admin_note": f"실시간 검증: lprice={price_check.naver_lprice:,.0f}원",
                })
                created += 1

        logger.info(f"✅ 정가거부 카페: {created}개 신규 | {skipped}개 스킵")
    except Exception as e:
        logger.error(f"❌ 정가거부 카페 sync: {e}")


async def _verify_prices():
    logger.info("🔍 가격 검증 시작...")
    try:
        import app.db_supabase as db
        from app.services.price_checker import verify_deal, MAX_FAIL_COUNT
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(minutes=8)).isoformat()
        deals = db.get_deals_for_verify(cutoff)
        logger.info(f"  검증 대상: {len(deals)}개")
        from app.services.price_scrapers import RealtimePriceChecker
        from app.config import settings
        rt_checker = RealtimePriceChecker(settings.NAVER_CLIENT_ID, settings.NAVER_CLIENT_SECRET)

        ok = changed = expired_count = 0
        async with __import__("httpx").AsyncClient(timeout=8) as hclient:
          for deal in deals:
            try:
                # 커뮤니티 딜: 핫딜 소진 여부 실시간 재확인
                if deal.get("source") == "community" and deal.get("sale_price"):
                    rt = await rt_checker.recheck_existing(
                        title=deal["title"],
                        stored_sale_price=float(deal["sale_price"]),
                        client=hclient,
                    )
                    if rt["action"] == "expired":
                        logger.info(f"  🛑 커뮤니티 딜 소진: {deal['title'][:40]} | {rt['reason']}")
                        db.update_deal_verify(deal["id"], {"status": "expired", "verify_fail_count": 0})
                        expired_count += 1
                        continue

                check = await verify_deal(deal)
                patch = {"last_verified_at": check["last_verified_at"].isoformat()}
                if check["verified_price"] is not None:
                    patch["verified_price"] = check["verified_price"]
                action = check["action"]
                fail = int(deal.get("verify_fail_count") or 0)
                if action == "url_dead":
                    fail += 1; patch["verify_fail_count"] = fail
                    if fail >= MAX_FAIL_COUNT: patch["status"] = "expired"; expired_count += 1
                elif action == "expired":
                    patch["status"] = "expired"; patch["verify_fail_count"] = 0; expired_count += 1
                elif action == "price_changed":
                    new_price = check.get("verified_price")
                    orig = float(deal.get("original_price") or 0)
                    # 커뮤니티 딜은 orig=0이므로 가격변동 만료 판단 불가 → 원글 만료 감지에 맡김
                    if deal.get("source") == "community" or orig <= 0:
                        patch["status"] = "active"  # 그냥 유지
                        patch["verify_fail_count"] = 0
                        ok += 1
                    # 현재가가 정가의 90% 이상 = 할인율 10% 미만 → 완전 만료
                    elif new_price and new_price >= orig * 0.90:
                        patch["status"] = "expired"
                        patch["verify_fail_count"] = 0
                        expired_count += 1
                        dr_now = round((1 - new_price / orig) * 100, 1)
                        logger.info(
                            f"  🛑 할인 소멸 만료: {deal.get('title','')[:40]} "
                            f"| 현재할인={dr_now}%"
                        )
                    else:
                        patch["status"] = "price_changed"
                        patch["verify_fail_count"] = 0
                        changed += 1
                elif action == "price_dropped":
                    # 네이버 최저가 < 우리 표시가 → sale_price 업데이트 (정확성 유지 핵심!)
                    new_price = check["verified_price"]
                    orig = float(deal.get("original_price") or 0)
                    patch["sale_price"] = new_price
                    patch["status"] = "active"
                    patch["verify_fail_count"] = 0
                    if orig > 0 and new_price < orig:
                        patch["discount_rate"] = round((1 - new_price / orig) * 100, 1)
                    ok += 1
                    logger.info(f"    ↓ 가격 업데이트: {int(deal.get('sale_price',0)):,} → {int(new_price):,}원")
                else:
                    patch["status"] = "active"; patch["verify_fail_count"] = 0; ok += 1
                # 가격 로그 insert (에러 무시)
                current_price = check.get("verified_price")
                if current_price is not None:
                    try:
                        db.get_supabase().table("deal_price_log").insert({
                            "deal_id": deal["id"],
                            "price": int(current_price),
                            "source": "verify"
                        }).execute()
                    except Exception:
                        pass
                db.update_deal_verify(deal["id"], patch)
            except Exception as e:
                logger.error(f"  딜 #{deal.get('id')} 검증 오류: {e}")
        logger.info(f"✅ 가격 검증 완료 — 정상:{ok} 변동:{changed} 만료:{expired_count}")
    except Exception as e:
        logger.error(f"❌ 가격 검증 오류: {e}")


async def _sync_brand_deals():
    """브랜드 공식 정가 × 네이버 현재가 비교 → 실제 할인 딜"""
    try:
        import app.db_supabase as db
        from app.services.brand_deals import collect_brand_deals
        from app.services.deal_validator import validator
        deals_data = await collect_brand_deals(min_discount=10)
        created = skipped = 0
        for item in deals_data:
            if db.deal_url_exists(item["product_url"]):
                continue
            v = validator.validate_sync(item)
            if not v:
                logger.debug(f"[브랜드skip] {v.reason}")
                skipped += 1
                continue
            # 제목+가격 중복 체크
            if db.deal_duplicate_exists(item["title"], v.sale_price):
                skipped += 1
                continue
            db.create_deal({
                "title": item["title"],
                "description": item.get("description"),
                "original_price": v.original_price,
                "sale_price": v.sale_price,
                "discount_rate": v.discount_rate,
                "image_url": item.get("image_url"),
                "product_url": item["product_url"],
                "source": "naver",
                "category": item.get("category", "기타"),
                "status": "active",
                "is_hot": v.is_hot,
                "submitter_name": item.get("brand", ""),
            })
            created += 1
        logger.info(f"✅ 브랜드딜 sync: {created}개 저장 | {skipped}개 제외")
    except Exception as e:
        logger.error(f"❌ 브랜드딜 sync: {e}")


async def _expire_old_deals():
    """3일 이상 된 딜 자동 만료"""
    try:
        import app.db_supabase as db
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        sb = db.get_supabase()
        result = sb.table("deals").update({"status": "expired"}).eq("status", "active").lt("created_at", cutoff).execute()
        count = len(result.data) if result.data else 0
        if count:
            logger.info(f"✅ 오래된 딜 만료: {count}개")
    except Exception as e:
        logger.error(f"❌ 딜 만료 처리 오류: {e}")


async def _sync_clien():
    """클리앙 핫딜 RSS 수집 — 2시간마다"""
    try:
        import app.db_supabase as db
        from app.services.clien import fetch_clien_deals

        deals_data = await fetch_clien_deals()
        created = skipped = 0

        for item in deals_data:
            source_post_url = item.get("source_post_url", "")

            # 이미 수집된 원글 스킵
            if source_post_url and db.deal_url_exists(source_post_url):
                skipped += 1
                continue

            product_url = item.get("product_url", "")
            if product_url and db.deal_url_exists(product_url):
                skipped += 1
                continue

            sale = float(item.get("sale_price") or 0)
            is_free = sale == 0

            if is_free and source_post_url:
                db.create_deal({
                    "title": item["title"],
                    "original_price": 0,
                    "sale_price": 0,
                    "discount_rate": 100,
                    "image_url": item.get("image_url"),
                    "product_url": source_post_url,
                    "source_post_url": source_post_url,
                    "source": "community",
                    "category": item.get("category", "기타"),
                    "status": "active",
                    "is_hot": False,
                    "submitter_name": item.get("submitter_name", "클리앙"),
                    "description": item.get("description"),
                })
                created += 1
                continue

            if sale <= 0:
                skipped += 1
                continue

            orig = float(item.get("original_price") or 0)
            discount_rate = float(item.get("discount_rate") or 0)

            if orig <= 0 or orig <= sale:
                skipped += 1
                continue
            if discount_rate < 10:
                skipped += 1
                continue

            if db.deal_duplicate_exists(item["title"], sale):
                skipped += 1
                continue

            db.create_deal({
                "title": item["title"],
                "description": item.get("description"),
                "original_price": orig,
                "sale_price": sale,
                "discount_rate": discount_rate,
                "image_url": item.get("image_url"),
                "product_url": product_url or source_post_url,
                "source_post_url": source_post_url,
                "source": "community",
                "category": item.get("category", "기타"),
                "status": "active",
                "is_hot": discount_rate >= 20,
                "submitter_name": item.get("submitter_name", "클리앙"),
            })
            logger.info(f"  ✅ [클리앙] 저장: {item['title'][:35]} | -{discount_rate}%")
            created += 1

        logger.info(f"✅ 클리앙 sync: {created}개 저장 | {skipped}개 제외")
    except Exception as e:
        logger.error(f"❌ 클리앙 sync: {e}")


async def _sync_algumon():
    """알구몬 API로 커뮤니티 딜 수집 (뽐뿌+루리웹+어미새+아카라이브)"""
    try:
        import app.db_supabase as db
        from app.services.algumon import fetch_algumon_deals, fetch_ruliweb_deals, process_algumon_deals
        from app.services.categorizer import infer_category

        # 최근 등록된 커뮤니티 딜 URL 목록 (중복 방지)
        sb = db.get_supabase()
        recent = sb.table("deals").select("product_url").eq("source", "community").limit(300).execute()
        existing_urls = {r["product_url"] for r in (recent.data or []) if r.get("product_url")}

        # 알구몬 5페이지 (50개) + 루리웹 RSS 병렬 수집
        algumon_raw, ruliweb_raw = await asyncio.gather(
            fetch_algumon_deals(pages=5),
            fetch_ruliweb_deals(),
            return_exceptions=True,
        )
        raw = []
        if isinstance(algumon_raw, list): raw.extend(algumon_raw)
        if isinstance(ruliweb_raw, list): raw.extend(ruliweb_raw)

        if not raw:
            return

        logger.info(f"[알구몬] 원본 {len(raw)}개 수집")
        processed = await process_algumon_deals(raw, existing_urls)
        logger.info(f"[알구몬] 필터 통과 {len(processed)}개")

        saved = 0
        for deal_data in processed:
            try:
                # 카테고리 추론
                if not deal_data.get("category") or deal_data["category"] == "기타":
                    deal_data["category"] = infer_category(deal_data["title"])

                db.create_deal({
                    "title": deal_data["title"],
                    "sale_price": deal_data["sale_price"],
                    "original_price": deal_data["original_price"],
                    "discount_rate": deal_data["discount_rate"],
                    "product_url": deal_data["product_url"],
                    "source_post_url": deal_data.get("source_post_url"),
                    "image_url": deal_data.get("image_url", ""),
                    "source": "community",
                    "category": deal_data["category"],
                    "description": deal_data.get("description", ""),
                })
                saved += 1
            except ValueError as e:
                logger.debug(f"[알구몬] 등록 거부: {e}")
            except Exception as e:
                if "duplicate" not in str(e).lower() and "unique" not in str(e).lower():
                    logger.warning(f"[알구몬] 등록 오류: {e}")

        if saved:
            logger.info(f"✅ 알구몬 {saved}개 등록 완료")

    except Exception as e:
        logger.error(f"❌ 알구몬 동기화 오류: {e}")


async def _check_community_deal_expiry():
    """모든 딜 원글 만료 감지 → 자동 expired 처리 (source 무관, source_post_url 있는 것 전체)"""
    try:
        import app.db_supabase as db
        from app.services.community_enricher import check_deal_expired_from_url
        import asyncio

        # 등록 후 1시간 이상 된 활성 딜 전체 체크 (source_post_url 있는 것)
        deals = db.get_community_deals_for_expiry_check(hours_since_created=1)
        if not deals:
            return

        logger.info(f"[원글 만료체크] {len(deals)}개 딜 확인 시작")
        expired_count = 0

        async def check_one(deal):
            nonlocal expired_count
            url = deal.get("source_post_url", "")
            if not url:
                return
            is_expired, reason = await check_deal_expired_from_url(url)
            if is_expired:
                db.expire_deal(deal["id"])
                # admin_note 업데이트
                db.get_supabase().table("deals").update({
                    "admin_note": f"[자동만료] 원글 종료 감지: {reason}"
                }).eq("id", deal["id"]).execute()
                expired_count += 1
                logger.info(f"  ✅ 만료처리: {deal['title'][:30]} ({reason})")

        # 동시에 최대 5개씩 체크 (과도한 요청 방지)
        for i in range(0, len(deals), 5):
            batch = deals[i:i+5]
            await asyncio.gather(*[check_one(d) for d in batch])
            await asyncio.sleep(1)

        if expired_count:
            logger.info(f"[커뮤니티 만료체크] 완료: {expired_count}/{len(deals)}개 만료")

    except Exception as e:
        logger.error(f"❌ 커뮤니티 만료체크 오류: {e}")


async def _collect_price_snapshots():
    """일일 가격 스냅샷 (브랜드딜 42종 현재가 저장)"""
    try:
        from app.services.price_history import collect_daily_snapshots
        saved = await collect_daily_snapshots()
        logger.info(f"[스냅샷] {saved}개 저장")
    except Exception as e:
        logger.error(f"[스냅샷] 오류: {e}")


async def _run_watchlist_monitor():
    """인기 제품 워치리스트 가격 모니터링 — 30분마다"""
    try:
        from app.services.watchlist_monitor import run_watchlist_monitor
        await run_watchlist_monitor()
    except Exception as e:
        logger.error(f"❌ 워치리스트 모니터 오류: {e}")


async def _run_kream_sync():
    """KREAM 트렌딩 → 워치리스트 갱신 — 주 1회"""
    try:
        from app.services.watchlist_monitor import run_kream_sync
        await run_kream_sync()
    except Exception as e:
        logger.error(f"❌ KREAM 동기화 오류: {e}")


def start_scheduler():
    """스케줄러 시작"""
    # 철칙 위반 딜 자동 만료 (5분마다)
    scheduler.add_job(
        _cleanup_invalid_deals,
        trigger=IntervalTrigger(minutes=5),
        id="cleanup_invalid",
        max_instances=1,
    )

    scheduler.add_job(
        _sync_coupang,
        trigger=IntervalTrigger(minutes=10),
        id="sync_coupang",
        name="쿠팡 딜 자동 동기화",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_naver,
        trigger=IntervalTrigger(minutes=30),
        id="sync_naver",
        name="네이버 딜 자동 동기화",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_ppomppu,
        trigger=IntervalTrigger(minutes=10),
        id="sync_ppomppu",
        name="뽐뿌 핫딜 자동 동기화 (비활성)",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_naver_cafe,
        trigger=IntervalTrigger(minutes=10),
        id="sync_naver_cafe",
        name="정가거부 카페 핫딜 수집 (비활성)",
        replace_existing=True,
    )
    scheduler.add_job(
        _verify_prices,
        trigger=IntervalTrigger(minutes=10),
        id="verify_prices",
        name="가격 검증 (10분마다)",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_brand_deals,
        trigger=IntervalTrigger(hours=2),
        id="sync_brand_deals",
        name="브랜드딜 정가 비교 동기화 (2h)",
        replace_existing=True,
    )
    scheduler.add_job(
        _expire_old_deals,
        trigger=IntervalTrigger(hours=6),
        id="expire_old_deals",
        name="오래된 딜 자동 만료 (3일 이상)",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_clien,
        trigger=IntervalTrigger(hours=2),
        id="sync_clien",
        name="클리앙 핫딜 RSS 동기화 (2h)",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_algumon,
        trigger=IntervalTrigger(minutes=20),
        id="sync_algumon",
        name="알구몬 커뮤니티 딜 동기화 (20m)",
        replace_existing=True,
    )
    scheduler.add_job(
        _check_community_deal_expiry,
        trigger=IntervalTrigger(minutes=10),
        id="community_expiry_check",
        name="원글 만료 자동 감지 — 전체 딜 (10m)",
        replace_existing=True,
    )
    scheduler.add_job(
        _collect_price_snapshots,
        trigger=IntervalTrigger(hours=24),
        id="price_snapshots",
        name="일일 가격 스냅샷 (브랜드딜 42종)",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_watchlist_monitor,
        trigger=IntervalTrigger(minutes=30),
        id="watchlist_monitor",
        name="인기 제품 워치리스트 가격 모니터링 (30분)",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_kream_sync,
        trigger=IntervalTrigger(weeks=1),
        id="kream_sync",
        name="KREAM 트렌딩 워치리스트 갱신 (주 1회)",
        replace_existing=True,
    )
    scheduler.start()
    msg = "🕐 스케줄러 시작: 워치리스트(30분) / 쿠팡(30분) / 네이버(1h) / 뽐뿌(30분) / 가격검증(1h) / 만료처리(6h)"
    logger.info(msg)
    print(msg, flush=True)  # uvicorn stdout에도 출력


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 스케줄러 종료")


async def _cleanup_invalid_deals():
    """5분마다: 할인율 0% or 식품/일상용품 커뮤니티 딜 자동 만료"""
    try:
        import app.db_supabase as db
        sb = db.get_supabase()

        # 1) 할인율 0% active 딜 — 커뮤니티 딜은 제외 (MSRP 없이 등록하는 방식)
        res = sb.table("deals").select("id,title,discount_rate,category,source") \
            .eq("status", "active") \
            .eq("discount_rate", 0) \
            .neq("source", "community") \
            .execute()
        for d in (res.data or []):
            # 무료딜(sale_price=0)은 예외
            sale_res = sb.table("deals").select("sale_price").eq("id", d["id"]).limit(1).execute()
            sale = float((sale_res.data or [{}])[0].get("sale_price", 1) or 1)
            if sale > 0:  # 유료딜인데 할인율 0 → 만료
                sb.table("deals").update({
                    "status": "expired",
                    "admin_note": "[자동만료] 할인율 0%"
                }).eq("id", d["id"]).execute()
                logger.info(f"🗑 자동만료(0%): #{d['id']} {d['title'][:35]}")

        # 2) 식품/일상용품 커뮤니티 딜 — 카테고리 기반 + 타이틀 키워드 2중 검사
        from app.services.community_enricher import is_food_or_daily
        BLOCKED_CATS = ["식품", "유아동"]
        res2 = sb.table("deals").select("id,title,category,source") \
            .eq("status", "active") \
            .eq("source", "community") \
            .execute()
        for d in (res2.data or []):
            cat = d.get("category", "")
            title = d.get("title", "")
            if cat in BLOCKED_CATS or is_food_or_daily(title, cat):
                sb.table("deals").update({
                    "status": "expired",
                    "admin_note": f"[자동만료] 식품/일상용품 커뮤니티 딜 철칙위반"
                }).eq("id", d["id"]).execute()
                logger.info(f"🗑 자동만료(식품): #{d['id']} {d['title'][:35]}")

        # 3) 할인율 10% 미만 active 딜 만료 (비커뮤니티 딜만 — 커뮤니티는 MSRP 없이 등록)
        res3 = sb.table("deals").select("id,title,discount_rate,sale_price,source") \
            .eq("status", "active") \
            .neq("source", "community") \
            .gt("sale_price", 0) \
            .lt("discount_rate", 10) \
            .gt("discount_rate", 0) \
            .execute()
        for d in (res3.data or []):
            sb.table("deals").update({
                "status": "expired",
                "admin_note": f"[자동만료] 할인율 {d['discount_rate']}% < 10%"
            }).eq("id", d["id"]).execute()
            logger.info(f"🗑 자동만료(할인<10%): #{d['id']} {d['title'][:35]} | {d['discount_rate']}%")

        # 4) is_hot 동기화: 할인율 40% 이상 → HOT, 미만 → not HOT
        res4 = sb.table("deals").select("id,discount_rate") \
            .eq("status", "active") \
            .eq("is_hot", False) \
            .gte("discount_rate", 40) \
            .execute()
        for d in (res4.data or []):
            sb.table("deals").update({"is_hot": True}).eq("id", d["id"]).execute()
            logger.info(f"⭐ is_hot 동기화: #{d['id']} {d['discount_rate']}%")
        # 할인율 40% 미만인데 HOT인 딜 해제
        res4b = sb.table("deals").select("id,discount_rate") \
            .eq("status", "active") \
            .eq("is_hot", True) \
            .lt("discount_rate", 40) \
            .execute()
        for d in (res4b.data or []):
            sb.table("deals").update({"is_hot": False}).eq("id", d["id"]).execute()
            logger.info(f"❄️ is_hot 해제: #{d['id']} {d['discount_rate']}%")

    except Exception as e:
        logger.error(f"❌ cleanup_invalid_deals 오류: {e}")
