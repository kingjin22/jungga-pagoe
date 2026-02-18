from fastapi import APIRouter
from datetime import datetime, timedelta
import app.db_supabase as db
from app.services.price_checker import verify_deal, MAX_FAIL_COUNT

router = APIRouter(prefix="/api/verify", tags=["verify"])


@router.post("/run")
async def run_price_verification():
    cutoff = (datetime.utcnow() - timedelta(minutes=55)).isoformat()
    deals = db.get_deals_for_verify(cutoff)

    results = {"checked": 0, "ok": 0, "price_changed": 0, "expired": 0, "url_dead": 0}

    for deal in deals:
        try:
            check = await verify_deal(deal)
            results["checked"] += 1

            patch = {"last_verified_at": check["last_verified_at"].isoformat()}
            if check["verified_price"] is not None:
                patch["verified_price"] = check["verified_price"]

            action = check["action"]
            fail_count = int(deal.get("verify_fail_count") or 0)

            if action == "url_dead":
                fail_count += 1
                patch["verify_fail_count"] = fail_count
                if fail_count >= MAX_FAIL_COUNT:
                    patch["status"] = "expired"
                    results["expired"] += 1
                else:
                    results["url_dead"] += 1
            elif action == "expired":
                patch["status"] = "expired"
                patch["verify_fail_count"] = 0
                results["expired"] += 1
            elif action == "price_changed":
                patch["status"] = "price_changed"
                patch["verify_fail_count"] = 0
                results["price_changed"] += 1
            else:
                patch["status"] = "active"
                patch["verify_fail_count"] = 0
                results["ok"] += 1

            db.update_deal_verify(deal["id"], patch)
        except Exception as e:
            print(f"검증 오류 #{deal.get('id')}: {e}")

    return {"message": f"{results['checked']}개 딜 검증 완료", **results}


@router.post("/{deal_id}")
async def verify_single(deal_id: int):
    deal = db.get_deal_by_id(deal_id)
    if not deal:
        return {"error": "딜 없음"}

    check = await verify_deal(deal)
    patch = {"last_verified_at": check["last_verified_at"].isoformat()}
    if check["verified_price"] is not None:
        patch["verified_price"] = check["verified_price"]

    action = check["action"]
    if action == "expired":
        patch["status"] = "expired"
    elif action == "price_changed":
        patch["status"] = "price_changed"
    elif action == "url_dead":
        fail = int(deal.get("verify_fail_count") or 0) + 1
        patch["verify_fail_count"] = fail
        if fail >= MAX_FAIL_COUNT:
            patch["status"] = "expired"
    else:
        patch["status"] = "active"
        patch["verify_fail_count"] = 0

    db.update_deal_verify(deal_id, patch)
    return {"id": deal_id, "action": action, **patch}


@router.get("/status")
async def verify_status():
    stats = db.get_stats()
    return {
        "summary": {
            "active": stats["total_deals"] - stats.get("expired", 0) - stats.get("price_changed", 0),
            "expired": stats.get("expired", 0),
            "price_changed": stats.get("price_changed", 0),
        }
    }
