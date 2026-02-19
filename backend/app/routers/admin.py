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
    return db.get_admin_metrics(date)


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
