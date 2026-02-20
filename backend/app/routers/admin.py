"""
Admin API Router
X-Admin-Key 헤더 인증 → settings.ADMIN_SECRET 비교
"""
from fastapi import APIRouter, HTTPException, Header, Query, BackgroundTasks
from typing import Optional
from pydantic import BaseModel
from app.config import settings
import app.db_supabase as db

router = APIRouter(prefix="/admin", tags=["admin"])


def verify_admin(x_admin_key: Optional[str] = Header(None)) -> None:
    """X-Admin-Key 헤더 검증"""
    if not x_admin_key or x_admin_key != settings.ADMIN_SECRET:
        raise HTTPException(status_code=403, detail="Forbidden: invalid admin key")


# ──────────────────────────────────────────
# Metrics
# ──────────────────────────────────────────

@router.get("/metrics")
async def get_metrics(
    date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    x_admin_key: Optional[str] = Header(None),
):
    verify_admin(x_admin_key)
    from fastapi.responses import JSONResponse
    data = db.get_admin_metrics(date)
    return JSONResponse(
        content=data,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        }
    )


# ──────────────────────────────────────────
# Deal List
# ──────────────────────────────────────────

@router.get("/deals")
async def get_admin_deals(
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    pinned: Optional[bool] = Query(None),
    sort: str = Query("latest"),
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=100),
    x_admin_key: Optional[str] = Header(None),
):
    verify_admin(x_admin_key)
    return db.get_admin_deals(
        status=status,
        source=source,
        search=search,
        pinned=pinned,
        sort=sort,
        page=page,
        size=size,
    )


# ──────────────────────────────────────────
# Deal Detail
# ──────────────────────────────────────────

@router.get("/deals/{deal_id}")
async def get_admin_deal(
    deal_id: int,
    x_admin_key: Optional[str] = Header(None),
):
    verify_admin(x_admin_key)
    deal = db.get_deal_admin(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return deal


# ──────────────────────────────────────────
# Deal Update
# ──────────────────────────────────────────

class DealAdminPatch(BaseModel):
    status: Optional[str] = None
    pinned: Optional[bool] = None
    admin_note: Optional[str] = None
    expires_at: Optional[str] = None
    is_hot: Optional[bool] = None
    category: Optional[str] = None
    title: Optional[str] = None
    image_url: Optional[str] = None
    sale_price: Optional[int] = None
    original_price: Optional[int] = None
    discount_rate: Optional[float] = None


@router.patch("/deals/{deal_id}")
async def patch_admin_deal(
    deal_id: int,
    body: DealAdminPatch,
    x_admin_key: Optional[str] = Header(None),
):
    verify_admin(x_admin_key)
    updated = db.update_deal_admin(deal_id, body.model_dump(exclude_none=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Deal not found or nothing to update")
    return updated


# ──────────────────────────────────────────
# 제보 검토 (Pending Review)
# ──────────────────────────────────────────

@router.get("/pending")
async def get_pending_deals(
    x_admin_key: Optional[str] = Header(None),
):
    """제보 대기 딜 목록 (pending + rejected 포함)"""
    verify_admin(x_admin_key)
    sb = db.get_supabase()
    res = sb.table("deals") \
        .select("*") \
        .in_("status", ["pending", "rejected"]) \
        .order("created_at", desc=True) \
        .limit(100) \
        .execute()
    return {"deals": res.data or [], "total": len(res.data or [])}


class ReviewBody(BaseModel):
    reason: Optional[str] = None  # 거부 사유 (선택)


@router.post("/deals/{deal_id}/approve")
async def approve_deal(
    deal_id: int,
    x_admin_key: Optional[str] = Header(None),
):
    """제보 딜 승인 → active"""
    verify_admin(x_admin_key)
    sb = db.get_supabase()
    deal = sb.table("deals").select("*").eq("id", deal_id).limit(1).execute().data
    if not deal:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")
    d = deal[0]

    # 철칙 검증
    orig = float(d.get("original_price") or 0)
    sale = float(d.get("sale_price") or 0)
    if sale > 0 and orig <= sale:
        raise HTTPException(status_code=400, detail=f"철칙 위반: original_price({orig}) <= sale_price({sale})")

    dr = round((1 - sale / orig) * 100, 1) if orig > sale > 0 else 0
    if dr <= 0:
        raise HTTPException(status_code=400, detail="할인율 0% — 승인 불가")

    sb.table("deals").update({
        "status": "active",
        "discount_rate": dr,
        "is_hot": dr >= 25,
        "admin_note": f"✅ 어드민 승인 | {d.get('admin_note', '')}",
    }).eq("id", deal_id).execute()

    return {"id": deal_id, "status": "active", "discount_rate": dr}


@router.post("/deals/{deal_id}/reject")
async def reject_deal(
    deal_id: int,
    body: ReviewBody,
    x_admin_key: Optional[str] = Header(None),
):
    """제보 딜 거부 → rejected"""
    verify_admin(x_admin_key)
    sb = db.get_supabase()
    reason = body.reason or "사유 미입력"
    sb.table("deals").update({
        "status": "rejected",
        "admin_note": f"❌ 거부: {reason}",
    }).eq("id", deal_id).execute()
    return {"id": deal_id, "status": "rejected", "reason": reason}


# ──────────────────────────────────────────
# Rescrape
# ──────────────────────────────────────────

@router.post("/deals/{deal_id}/rescrape")
async def rescrape_deal(
    deal_id: int,
    background_tasks: BackgroundTasks,
    x_admin_key: Optional[str] = Header(None),
):
    verify_admin(x_admin_key)
    deal = db.get_deal_by_id(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    if deal.get("source") == "naver":
        def run_rescrape():
            try:
                from app.services.brand_deals import run_brand_deals
                run_brand_deals()
            except Exception as e:
                print(f"[rescrape] error: {e}")

        background_tasks.add_task(run_rescrape)
        return {"status": "rescrape_queued", "source": "naver"}
    else:
        return {"status": "not_supported", "source": deal.get("source"), "message": "naver 소스만 재수집 지원"}
