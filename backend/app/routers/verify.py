"""
가격 검증 라우터
- POST /api/verify/run        : 전체 활성 딜 가격 일괄 검증
- POST /api/verify/{deal_id}  : 특정 딜 단건 검증
- GET  /api/verify/status     : 최근 검증 현황
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta

from app.database import get_db
from app.models.deal import Deal, DealStatus
from app.services.price_checker import verify_deal, MAX_FAIL_COUNT

router = APIRouter(prefix="/api/verify", tags=["verify"])


@router.post("/run")
async def run_price_verification(db: Session = Depends(get_db)):
    """
    모든 활성 딜 + 가격변동 딜 대상으로 가격 검증 실행
    - ACTIVE, PRICE_CHANGED 상태만 대상
    - 마지막 검증 후 30분 이상 지난 딜만 재검증
    """
    cutoff = datetime.utcnow() - timedelta(minutes=30)

    deals = db.query(Deal).filter(
        Deal.status.in_([DealStatus.ACTIVE, DealStatus.PRICE_CHANGED]),
        (Deal.last_verified_at == None) | (Deal.last_verified_at < cutoff),
    ).all()

    print(f"\n[가격 검증] 대상 딜: {len(deals)}개")

    results = {"checked": 0, "ok": 0, "price_changed": 0, "expired": 0, "url_dead": 0}

    for deal in deals:
        try:
            check = await verify_deal(deal)
            results["checked"] += 1

            deal.last_verified_at = check["last_verified_at"]
            if check["verified_price"] is not None:
                deal.verified_price = check["verified_price"]

            action = check["action"]

            if action == "url_dead":
                deal.verify_fail_count = (deal.verify_fail_count or 0) + 1
                if deal.verify_fail_count >= MAX_FAIL_COUNT:
                    deal.status = DealStatus.EXPIRED
                    print(f"    → 만료 처리 (URL 연속 {MAX_FAIL_COUNT}회 실패)")
                    results["expired"] += 1
                else:
                    results["url_dead"] += 1

            elif action == "expired":
                deal.status = DealStatus.EXPIRED
                deal.verify_fail_count = 0
                results["expired"] += 1

            elif action == "price_changed":
                deal.status = DealStatus.PRICE_CHANGED
                deal.verify_fail_count = 0
                results["price_changed"] += 1

            else:  # ok
                deal.status = DealStatus.ACTIVE
                deal.verify_fail_count = 0
                results["ok"] += 1

            db.commit()

        except Exception as e:
            print(f"  [검증 오류] #{deal.id}: {e}")
            continue

    print(f"[가격 검증] 완료: {results}")
    return {
        "message": f"{results['checked']}개 딜 검증 완료",
        **results,
    }


@router.post("/{deal_id}")
async def verify_single_deal(deal_id: int, db: Session = Depends(get_db)):
    """특정 딜 단건 가격 검증"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")

    check = await verify_deal(deal)

    deal.last_verified_at = check["last_verified_at"]
    if check["verified_price"] is not None:
        deal.verified_price = check["verified_price"]

    action = check["action"]
    if action == "expired":
        deal.status = DealStatus.EXPIRED
    elif action == "price_changed":
        deal.status = DealStatus.PRICE_CHANGED
    elif action == "url_dead":
        deal.verify_fail_count = (deal.verify_fail_count or 0) + 1
        if deal.verify_fail_count >= MAX_FAIL_COUNT:
            deal.status = DealStatus.EXPIRED
    else:
        deal.status = DealStatus.ACTIVE
        deal.verify_fail_count = 0

    db.commit()
    db.refresh(deal)

    return {
        "id": deal.id,
        "status": deal.status,
        "verified_price": deal.verified_price,
        "registered_price": deal.sale_price,
        "change_pct": check.get("change_pct", 0),
        "url_alive": check.get("url_alive", True),
        "last_verified_at": deal.last_verified_at,
    }


@router.get("/status")
async def get_verification_status(db: Session = Depends(get_db)):
    """검증 현황 통계"""
    total_active = db.query(Deal).filter(Deal.status == DealStatus.ACTIVE).count()
    total_expired = db.query(Deal).filter(Deal.status == DealStatus.EXPIRED).count()
    total_price_changed = db.query(Deal).filter(Deal.status == DealStatus.PRICE_CHANGED).count()

    never_verified = db.query(Deal).filter(
        Deal.status == DealStatus.ACTIVE,
        Deal.last_verified_at == None,
    ).count()

    recent_verified = db.query(Deal).filter(
        Deal.last_verified_at != None,
    ).order_by(Deal.last_verified_at.desc()).limit(5).all()

    return {
        "summary": {
            "active": total_active,
            "expired": total_expired,
            "price_changed": total_price_changed,
            "never_verified": never_verified,
        },
        "recent_verifications": [
            {
                "id": d.id,
                "title": d.title[:40],
                "status": d.status,
                "verified_price": d.verified_price,
                "sale_price": d.sale_price,
                "last_verified_at": d.last_verified_at,
            }
            for d in recent_verified
        ],
    }
