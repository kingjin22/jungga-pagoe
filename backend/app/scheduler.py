"""
APScheduler 백그라운드 자동 동기화
- 매 30분: 쿠팡 딜 sync
- 매 1시간: 네이버 딜 sync
"""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _sync_coupang():
    """쿠팡 딜 자동 동기화"""
    try:
        from app.database import SessionLocal
        from app.models.deal import Deal, DealSource, DealStatus
        from app.services.coupang import get_best_deals
        import math

        db = SessionLocal()
        try:
            deals_data = await get_best_deals(limit=30)
            created = 0

            for item in deals_data:
                existing = db.query(Deal).filter(Deal.product_url == item["product_url"]).first()
                if existing:
                    continue

                original = item.get("original_price", 0)
                sale = item.get("sale_price", 0)
                if original <= 0 or sale <= 0:
                    continue
                discount_rate = round((1 - sale / original) * 100, 1)
                if discount_rate < 5:
                    continue

                deal = Deal(
                    title=item["title"],
                    original_price=original,
                    sale_price=sale,
                    discount_rate=discount_rate,
                    image_url=item.get("image_url"),
                    product_url=item["product_url"],
                    affiliate_url=item.get("affiliate_url"),
                    source=DealSource.COUPANG,
                    status=DealStatus.ACTIVE,
                    is_hot=discount_rate >= 40,
                )
                db.add(deal)
                created += 1

            db.commit()
            logger.info(f"✅ 쿠팡 자동 sync: {created}개 신규 딜")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ 쿠팡 sync 오류: {e}")


async def _sync_naver():
    """네이버 딜 자동 동기화"""
    try:
        from app.database import SessionLocal
        from app.models.deal import Deal, DealSource, DealStatus
        from app.services.naver import get_hot_deals

        db = SessionLocal()
        try:
            deals_data = await get_hot_deals()
            created = 0

            for item in deals_data:
                existing = db.query(Deal).filter(Deal.product_url == item["product_url"]).first()
                if existing:
                    continue

                original = item.get("original_price", 0)
                sale = item.get("sale_price", 0)
                if original <= 0 or sale <= 0:
                    continue
                discount_rate = round((1 - sale / original) * 100, 1)
                if discount_rate < 5:
                    continue

                deal = Deal(
                    title=item["title"],
                    original_price=original,
                    sale_price=sale,
                    discount_rate=discount_rate,
                    image_url=item.get("image_url"),
                    product_url=item["product_url"],
                    source=DealSource.NAVER,
                    status=DealStatus.ACTIVE,
                    is_hot=discount_rate >= 40,
                )
                db.add(deal)
                created += 1

            db.commit()
            logger.info(f"✅ 네이버 자동 sync: {created}개 신규 딜")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"❌ 네이버 sync 오류: {e}")


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
    scheduler.start()
    logger.info("🕐 APScheduler 시작: 쿠팡(30분), 네이버(1시간) 자동 sync")


def stop_scheduler():
    """스케줄러 종료"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 APScheduler 종료")
