"""
APScheduler 백그라운드 자동 작업
- 매 30분  : 쿠팡 딜 sync
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
        deals_data = await collect_real_deals(limit_per_keyword=5)
        created = 0
        for item in deals_data:
            if db.deal_url_exists(item["product_url"]):
                continue
            orig, sale = item.get("original_price", 0), item.get("sale_price", 0)
            if orig <= 0 or sale <= 0: continue
            dr = round((1 - sale / orig) * 100, 1)
            if dr < 10: continue
            db.create_deal({"title": item["title"], "original_price": orig, "sale_price": sale,
                "discount_rate": dr, "image_url": item.get("image_url"),
                "product_url": item["product_url"], "source": "naver",
                "category": item.get("category", "기타"), "status": "active", "is_hot": dr >= 40})
            created += 1
        logger.info(f"✅ 네이버 sync: {created}개")
    except Exception as e:
        logger.error(f"❌ 네이버 sync: {e}")


async def _sync_ppomppu():
    try:
        import app.db_supabase as db
        from app.services.ppomppu import fetch_ppomppu_deals
        from app.services.naver import search_product

        OVERSEAS_RETAILERS = ["[ebay]", "[amazon]", "[woot]", "[costco]", "[asus.com]",
                              "[아마존재팬]", "[아마존]", "[bestbuy]", "[walmart]", "[aliexpress]",
                              "[미국 costco]", "[amazon.com]"]
        MIN_DISCOUNT = 10   # 커뮤니티 딜도 10% 이상만
        # 가격 조작 방지: 네이버 lprice 대비 너무 싸면 가품/오류 의심 (카테고리별 하한선)
        MIN_PRICE_RATIO = 0.15  # 네이버 lprice의 15% 미만이면 스킵

        deals_data = await fetch_ppomppu_deals()
        created = skipped_no_discount = skipped_naver_mismatch = 0

        for item in deals_data:
            sale = item.get("sale_price", 0)
            if sale < 0:
                continue

            # 해외 리테일러 차단
            title_lower = item.get("title", "").lower()
            if any(r in title_lower for r in OVERSEAS_RETAILERS):
                continue

            # 품질 기준: 이미지 + 실제 쇼핑몰 URL (무료 제외)
            has_image = bool(item.get("image_url"))
            has_real_url = bool(item["product_url"] and "ppomppu.co.kr" not in item["product_url"])
            is_free = sale == 0
            if not is_free and not (has_image and has_real_url):
                continue

            if db.deal_url_exists(item["product_url"]):
                continue

            # ─── 네이버 시세 크로스체크 ───────────────────────────
            final_original = item.get("original_price", 0) or 0
            final_dr = item.get("discount_rate", 0.0) or 0.0
            naver_verified = False

            if not is_free and sale > 0:
                try:
                    naver = await search_product(item["title"])
                    naver_lprice = naver.get("naver_lprice")  # 네이버 현재 최저가
                    naver_hprice = naver.get("naver_hprice")  # 네이버 최고가(정가)

                    if naver_lprice and naver_lprice > 0:
                        # 가품 방지: 커뮤니티 가격이 네이버 최저가의 15% 미만이면 이상
                        if sale < naver_lprice * MIN_PRICE_RATIO:
                            skipped_naver_mismatch += 1
                            continue

                        # 기준가: 네이버 hprice(정가) > lprice 있으면 사용, 없으면 lprice
                        naver_ref = naver_hprice if (naver_hprice and naver_hprice > naver_lprice) else naver_lprice

                        if sale < naver_ref:
                            # 네이버 기준가 대비 실제 할인 확인됨
                            naver_dr = round((1 - sale / naver_ref) * 100, 1)
                            if naver_dr >= MIN_DISCOUNT:
                                final_original = naver_ref
                                final_dr = naver_dr
                                naver_verified = True
                            else:
                                skipped_no_discount += 1
                                continue
                        else:
                            # 커뮤니티 가격이 네이버 최저가보다 비쌈 → 딜 아님
                            skipped_no_discount += 1
                            continue
                    else:
                        # 네이버 결과 없음 → 제목 파싱 할인율로 판단
                        if final_dr < MIN_DISCOUNT and not (final_original > sale > 0 and
                           round((1 - sale / final_original) * 100, 1) >= MIN_DISCOUNT):
                            skipped_no_discount += 1
                            continue
                        # 제목 파싱 할인율 재계산
                        if final_original > sale > 0:
                            final_dr = round((1 - sale / final_original) * 100, 1)
                except Exception as e:
                    logger.warning(f"네이버 검증 실패 [{item['title'][:30]}]: {e}")
                    # 검증 실패 시 기존 로직 fallback
                    if final_dr < MIN_DISCOUNT and not (final_original > sale > 0):
                        skipped_no_discount += 1
                        continue
            # ──────────────────────────────────────────────────────

            db.create_deal({
                "title": item["title"],
                "description": item.get("description"),
                "original_price": final_original or sale,
                "sale_price": sale,
                "discount_rate": final_dr,
                "image_url": item.get("image_url"),
                "product_url": item["product_url"],
                "source": "community",
                "category": item.get("category", "기타"),
                "status": "active",
                "is_hot": final_dr >= 20 or item.get("is_hot", False),
                "submitter_name": item.get("submitter_name", "뽐뿌"),
                # 네이버 검증 여부를 admin_note에 기록
                "admin_note": "네이버 시세 검증 완료" if naver_verified else None,
            })
            created += 1

        logger.info(f"✅ 뽐뿌 sync: {created}개 저장 | 할인없음 {skipped_no_discount}개 제외 | 가격이상 {skipped_naver_mismatch}개 제외")
    except Exception as e:
        logger.error(f"❌ 뽐뿌 sync: {e}")


async def _verify_prices():
    logger.info("🔍 가격 검증 시작...")
    try:
        import app.db_supabase as db
        from app.services.price_checker import verify_deal, MAX_FAIL_COUNT
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(minutes=55)).isoformat()
        deals = db.get_deals_for_verify(cutoff)
        logger.info(f"  검증 대상: {len(deals)}개")
        ok = changed = expired_count = 0
        for deal in deals:
            try:
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
        deals_data = await collect_brand_deals(min_discount=10)
        created = 0
        for item in deals_data:
            if db.deal_url_exists(item["product_url"]):
                continue
            dr = item.get("discount_rate", 0)
            db.create_deal({
                "title": item["title"],
                "description": item.get("description"),
                "original_price": item["original_price"],
                "sale_price": item["sale_price"],
                "discount_rate": dr,
                "image_url": item.get("image_url"),
                "product_url": item["product_url"],
                "source": "naver",
                "category": item.get("category", "기타"),
                "status": "active",
                "is_hot": dr >= 20,
                "submitter_name": item.get("brand", ""),  # 브랜드명 저장 (신뢰지수용)
            })
            created += 1
        logger.info(f"✅ 브랜드딜 sync: {created}개")
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
        trigger=IntervalTrigger(minutes=30),
        id="sync_coupang",
        name="쿠팡 딜 자동 동기화",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_naver,
        trigger=IntervalTrigger(hours=1),
        id="sync_naver",
        name="네이버 딜 자동 동기화",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_ppomppu,
        trigger=IntervalTrigger(minutes=30),
        id="sync_ppomppu",
        name="뽐뿌 핫딜 자동 동기화",
        replace_existing=True,
    )
    scheduler.add_job(
        _verify_prices,
        trigger=IntervalTrigger(hours=1),
        id="verify_prices",
        name="가격 검증 (자동 비활성)",
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
