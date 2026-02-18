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
            if db.deal_url_exists(item["product_url"]):
                continue
            dr = item.get("discount_rate", 15.0)
            db.create_deal({"title": item["title"], "description": item.get("description"),
                "original_price": item["original_price"], "sale_price": item["sale_price"],
                "discount_rate": dr, "image_url": item.get("image_url"),
                "product_url": item["product_url"], "source": "community",
                "category": item.get("category", "기타"), "status": "active",
                "is_hot": dr >= 40, "submitter_name": "뽐뿌"})
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
    scheduler.start()
    logger.info("🕐 스케줄러 시작: 쿠팡(30분) / 네이버(1h) / 뽐뿌(30분) / 가격검증(1h)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 스케줄러 종료")
