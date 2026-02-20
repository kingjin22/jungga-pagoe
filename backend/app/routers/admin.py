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
    """제보 딜 거부 → expired (DB enum에 rejected 없음)"""
    verify_admin(x_admin_key)
    sb = db.get_supabase()
    reason = body.reason or "사유 미입력"
    sb.table("deals").update({
        "status": "expired",
        "admin_note": f"[거부] {reason}",
    }).eq("id", deal_id).execute()
    return {"id": deal_id, "status": "expired", "reason": reason}


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


# ──────────────────────────────────────────
# 어드민 빠른 딜 등록
# ──────────────────────────────────────────

class QuickAddDeal(BaseModel):
    product_url: str
    title: str
    sale_price: int
    original_price: int
    category: str = ""
    image_url: str = ""
    description: str = ""
    source: str = "admin"
    brand: str = ""


@router.get("/lookup")
async def lookup_product(
    q: str = Query(..., description="상품명 또는 URL"),
    x_admin_key: Optional[str] = Header(None),
):
    """상품명/URL → Naver 검색으로 제목·정가·이미지 자동 완성"""
    verify_admin(x_admin_key)
    import re
    # URL이 오면 핵심 키워드 추출
    keyword = q
    if q.startswith("http"):
        # 쿠팡 등 URL에서 상품명 추출 시도
        keyword = re.sub(r"https?://[^\s]+", "", q).strip() or q
        # URL 마지막 path segment 활용
        parts = q.rstrip("/").split("/")
        for p in reversed(parts):
            p = re.sub(r"[^가-힣a-zA-Z0-9\s]", " ", p).strip()
            if len(p) > 5:
                keyword = p
                break

    try:
        import urllib.request, urllib.parse
        from app.config import settings
        headers = {
            "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
        }
        query = urllib.parse.urlencode({"query": keyword, "display": 5, "sort": "sim"})
        req = urllib.request.Request(
            f"https://openapi.naver.com/v1/search/shop.json?{query}", headers=headers
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            import json, re as _re
            data = json.loads(r.read())
        items = data.get("items", [])
        results = []
        for item in items[:3]:
            clean_title = _re.sub(r"<[^>]+>", "", item.get("title", ""))
            results.append({
                "title": clean_title,
                "lprice": int(item.get("lprice") or 0),
                "hprice": int(item.get("hprice") or 0),
                "image": item.get("image", ""),
                "brand": item.get("brand", ""),
                "category": item.get("category1", ""),
            })
        return {"results": results, "keyword": keyword}
    except Exception as e:
        return {"results": [], "error": str(e), "keyword": keyword}


@router.post("/deals/quick-add")
async def quick_add_deal(
    body: QuickAddDeal,
    x_admin_key: Optional[str] = Header(None),
):
    """어드민 직접 등록 — 검증 없이 바로 active"""
    verify_admin(x_admin_key)
    from app.services.categorizer import infer_category

    orig = body.original_price
    sale = body.sale_price

    # 철칙 최소 검증 (무료딜 제외)
    if sale > 0 and orig <= sale:
        raise HTTPException(status_code=400, detail=f"정가({orig})가 할인가({sale})보다 낮거나 같습니다")

    dr = round((1 - sale / orig) * 100, 1) if orig > 0 and sale > 0 else 100.0
    if sale > 0 and dr <= 0:
        raise HTTPException(status_code=400, detail="할인율이 0 이하입니다")

    category = body.category if body.category and body.category != "기타" \
        else infer_category(body.title)

    deal_data = {
        "title": body.title.strip(),
        "product_url": body.product_url.strip(),
        "sale_price": sale,
        "original_price": orig,
        "discount_rate": dr,
        "image_url": body.image_url.strip(),
        "category": category,
        "source": body.source,
        "description": body.description.strip(),
        "status": "active",  # 어드민 등록 → 바로 active
    }
    if body.brand:
        deal_data["brand"] = body.brand

    try:
        deal = db.create_deal(deal_data)
        # 이미지 없으면 Naver에서 자동 주입
        if not deal_data.get("image_url") and deal:
            from app.routers.deals import _fetch_naver_image
            image = await _fetch_naver_image(deal_data["title"])
            if image:
                db.get_supabase().table("deals").update({"image_url": image}).eq("id", deal["id"]).execute()
                deal["image_url"] = image
        return deal
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
