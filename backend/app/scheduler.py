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
    """쿠팡 딜 자동 동기화"""
    try:
        from app.database import SessionLocal
        from app.models.deal import Deal, DealSource, DealStatus
        from app.services.coupang import get_best_deals

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


async def _verify_prices():
    """
    가격 검증 스케줄 작업
    활성 딜 전체의 현재 가격을 확인하고, 가격이 올랐으면 비활성 처리
    """
    logger.info("🔍 가격 검증 시작...")
    try:
        from app.database import SessionLocal
        from app.models.deal import Deal, DealStatus
        from app.services.price_checker import verify_deal, MAX_FAIL_COUNT
        from datetime import datetime, timedelta

        db = SessionLocal()
        try:
            cutoff = datetime.utcnow() - timedelta(minutes=55)  # 55분 이상 지난 딜만
            deals = db.query(Deal).filter(
                Deal.status.in_([DealStatus.ACTIVE, DealStatus.PRICE_CHANGED]),
                (Deal.last_verified_at == None) | (Deal.last_verified_at < cutoff),
            ).all()

            logger.info(f"  검증 대상: {len(deals)}개")
            ok, changed, expired_count = 0, 0, 0

            for deal in deals:
                try:
                    check = await verify_deal(deal)
                    deal.last_verified_at = check["last_verified_at"]
                    if check["verified_price"] is not None:
                        deal.verified_price = check["verified_price"]

                    action = check["action"]
                    if action == "url_dead":
                        deal.verify_fail_count = (deal.verify_fail_count or 0) + 1
                        if deal.verify_fail_count >= MAX_FAIL_COUNT:
                            deal.status = DealStatus.EXPIRED
                            expired_count += 1
                    elif action == "expired":
                        deal.status = DealStatus.EXPIRED
                        deal.verify_fail_count = 0
                        expired_count += 1
                    elif action == "price_changed":
                        deal.status = DealStatus.PRICE_CHANGED
                        deal.verify_fail_count = 0
                        changed += 1
                    else:
                        deal.status = DealStatus.ACTIVE
                        deal.verify_fail_count = 0
                        ok += 1

                    db.commit()
                except Exception as e:
                    logger.error(f"  딜 #{deal.id} 검증 오류: {e}")

            logger.info(f"✅ 가격 검증 완료 — 정상:{ok} 변동:{changed} 만료:{expired_count}")
        finally:
            db.close()
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
        _verify_prices,
        trigger=IntervalTrigger(hours=1),
        id="verify_prices",
        name="가격 검증 (자동 비활성)",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("🕐 스케줄러 시작: 쿠팡(30분) / 네이버(1h) / 가격검증(1h)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 스케줄러 종료")
