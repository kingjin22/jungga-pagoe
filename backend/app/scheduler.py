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
    # ⛔ 영구 비활성화 — Naver lprice 기반 검증으로는 딜 소진 감지 불가
    # 실제 쇼핑몰 페이지 직접 가격 크롤링 구현 전까지 수집 중단
    logger.info("⛔ 뽐뿌 sync 비활성화")
    return
    try:
        import app.db_supabase as db
        from app.services.ppomppu import fetch_ppomppu_deals
        from app.services.price_scrapers import check_community_deal_price
        from app.config import settings

        deals_data = await fetch_ppomppu_deals()
        created = skipped = 0

        async with __import__("httpx").AsyncClient(timeout=8) as client:
            for item in deals_data:
                sale = float(item.get("sale_price") or 0)
                is_free = sale == 0

                # 품질 기준: 이미지 + 실제 쇼핑몰 URL (무료 제외)
                if not is_free:
                    has_image = bool(item.get("image_url"))
                    has_real_url = bool(item.get("product_url") and "ppomppu.co.kr" not in item["product_url"])
                    if not (has_image and has_real_url):
                        skipped += 1
                        continue

                if db.deal_url_exists(item["product_url"]):
                    continue

                if is_free:
                    # 무료딜은 검증 없이 저장
                    db.create_deal({
                        "title": item["title"],
                        "original_price": 0,
                        "sale_price": 0,
                        "discount_rate": 100,
                        "image_url": item.get("image_url"),
                        "product_url": item["product_url"],
                        "source": "community",
                        "category": item.get("category", "기타"),
                        "status": "active",
                        "is_hot": False,
                        "submitter_name": item.get("submitter_name", "뽐뿌"),
                    })
                    created += 1
                    continue

                # ── 실시간 가격 유효성 검증 ──────────────────────
                price_check = await check_community_deal_price(
                    title=item["title"],
                    community_price=sale,
                    naver_client_id=settings.NAVER_CLIENT_ID,
                    naver_client_secret=settings.NAVER_CLIENT_SECRET,
                    client=client,
                )
                if not price_check:
                    logger.debug(f"[뽐뿌skip] {price_check.reason} | {item['title'][:40]}")
                    skipped += 1
                    continue

                # 중복 체크 (네이버 카탈로그 URL 기준)
                final_url = price_check.naver_product_url or item["product_url"]
                if db.deal_url_exists(final_url):
                    skipped += 1
                    continue
                if db.deal_duplicate_exists(item["title"], price_check.community_price):
                    skipped += 1
                    continue

                db.create_deal({
                    "title": item["title"],
                    "description": item.get("description"),
                    "original_price": price_check.naver_hprice or price_check.naver_lprice,
                    "sale_price": price_check.community_price,
                    "discount_rate": price_check.discount_vs_hprice,
                    "image_url": item.get("image_url") or price_check.image_url,
                    "product_url": final_url,
                    "source": "community",
                    "category": item.get("category", "기타"),
                    "status": "active",
                    "is_hot": price_check.discount_vs_hprice >= 20,
                    "submitter_name": item.get("submitter_name", "뽐뿌"),
                    "admin_note": f"실시간 검증: lprice={price_check.naver_lprice:,.0f}원",
                })
                logger.info(f"  ✅ 저장: {item['title'][:40]} | -{price_check.discount_vs_hprice}%")
                created += 1

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
                    patch["status"] = "price_changed"; patch["verify_fail_count"] = 0; changed += 1
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


async def _collect_price_snapshots():
    """일일 가격 스냅샷 (브랜드딜 42종 현재가 저장)"""
    try:
        from app.services.price_history import collect_daily_snapshots
        saved = await collect_daily_snapshots()
        logger.info(f"[스냅샷] {saved}개 저장")
    except Exception as e:
        logger.error(f"[스냅샷] 오류: {e}")


def start_scheduler():
    """스케줄러 시작"""
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
        _collect_price_snapshots,
        trigger=IntervalTrigger(hours=24),
        id="price_snapshots",
        name="일일 가격 스냅샷 (브랜드딜 42종)",
        replace_existing=True,
    )
    scheduler.start()
    msg = "🕐 스케줄러 시작: 쿠팡(30분) / 네이버(1h) / 뽐뿌(30분) / 가격검증(1h) / 만료처리(6h)"
    logger.info(msg)
    print(msg, flush=True)  # uvicorn stdout에도 출력


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 스케줄러 종료")
