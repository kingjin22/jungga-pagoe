"""
통계 API
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date

from app.database import get_db
from app.models.deal import Deal, DealSource, DealStatus

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def get_stats(db: Session = Depends(get_db)):
    """전체 통계 조회"""
    # 전체 활성 딜 수
    total_deals = db.query(Deal).filter(Deal.status == DealStatus.ACTIVE).count()

    # 핫딜 수
    hot_deals = db.query(Deal).filter(
        Deal.status == DealStatus.ACTIVE,
        Deal.is_hot == True
    ).count()

    # 소스별 딜 수
    by_source = {}
    for source in DealSource:
        count = db.query(Deal).filter(
            Deal.status == DealStatus.ACTIVE,
            Deal.source == source
        ).count()
        by_source[source.value] = count

    # 오늘 등록된 딜 수
    today_start = datetime.combine(date.today(), datetime.min.time())
    today_added = db.query(Deal).filter(
        Deal.created_at >= today_start
    ).count()

    # 평균 할인율
    avg_discount_result = db.query(func.avg(Deal.discount_rate)).filter(
        Deal.status == DealStatus.ACTIVE
    ).scalar()
    avg_discount = round(float(avg_discount_result), 1) if avg_discount_result else 0.0

    return {
        "total_deals": total_deals,
        "hot_deals": hot_deals,
        "by_source": by_source,
        "today_added": today_added,
        "avg_discount": avg_discount,
    }
