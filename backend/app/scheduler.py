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
    try:
        import app.db_supabase as db
        from app.services.coupang import get_best_deals
        deals_data = await get_best_deals(limit=30)
        created = 0
        for item in deals_data:
            if db.deal_url_exists(item["product_url"]):
                continue
            orig, sale = item.get("original_price", 0), item.get("sale_price", 0)
            if orig <= 0 or sale <= 0: continue
            dr = round((1 - sale / orig) * 100, 1)
            if dr < 5: continue
            db.create_deal({"title": item["title"], "original_price": orig, "sale_price": sale,
                "discount_rate": dr, "image_url": item.get("image_url"),
                "product_url": item["product_url"], "affiliate_url": item.get("affiliate_url"),
                "source": "coupang", "status": "active", "is_hot": dr >= 40})
            created += 1
        logger.info(f"✅ 쿠팡 sync: {created}개")
    except Exception as e:
        logger.error(f"❌ 쿠팡 sync: {e}")


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
        deals_data = await fetch_ppomppu_deals()
        created = 0
        for item in deals_data:
            sale = item.get("sale_price", 0)
            if sale < 0: continue
            # 해외 리테일러 딜 차단: 영문 제목 → 네이버가 엉뚱한 제품 매칭 → 가격/이미지 틀림
            OVERSEAS_RETAILERS = ["[ebay]", "[amazon]", "[woot]", "[costco]", "[asus.com]",
                                  "[아마존재팬]", "[아마존]", "[bestbuy]", "[walmart]", "[aliexpress]",
                                  "[미국 costco]", "[amazon.com]"]
            title_lower = item.get("title", "").lower()
            if any(r in title_lower for r in OVERSEAS_RETAILERS):
                continue

            # 품질 기준: 이미지 있거나 실제 쇼핑몰 URL이 있어야 저장
            has_image = bool(item.get("image_url"))
            has_real_url = item["product_url"] and "ppomppu.co.kr" not in item["product_url"]
            is_free = sale == 0  # 무료 딜은 이미지 없어도 저장
            if not (has_image or has_real_url or is_free):
                continue
            if db.deal_url_exists(item["product_url"]):
                continue
            dr = item.get("discount_rate", 0.0)
            db.create_deal({"title": item["title"], "description": item.get("description"),
                "original_price": item.get("original_price", sale), "sale_price": sale,
                "discount_rate": dr, "image_url": item.get("image_url"),
                "product_url": item["product_url"], "source": "community",
                "category": item.get("category", "기타"), "status": "active",
                "is_hot": dr >= 20 or item.get("is_hot", False),
                "submitter_name": item.get("submitter_name", "뽐뿌")})
            created += 1
        logger.info(f"✅ 뽐뿌 sync: {created}개")
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
