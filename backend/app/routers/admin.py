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
    """제보 대기 딜 목록 (pending만 — rejected는 DB enum 없음, expired+[거부] 메모로 대체)"""
    verify_admin(x_admin_key)
    sb = db.get_supabase()
    res = sb.table("deals") \
        .select("*") \
        .eq("status", "pending") \
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

    # URL로 소스 자동 감지
    url = body.product_url.lower()
    if body.source in ("admin", "community"):
        if "coupang.com" in url or "coupa.ng" in url or "coupang.net" in url:
            detected_source = "coupang"
        elif "naver.com" in url or "smartstore" in url:
            detected_source = "naver"
        else:
            detected_source = body.source
    else:
        detected_source = body.source

    # 쿠팡 URL → 파트너스 링크 자동 변환 (link.coupang.com이 아닐 때)
    final_url = body.product_url.strip()
    if detected_source == "coupang" and "link.coupang.com" not in url:
        try:
            from app.services.coupang_partners import generate_affiliate_link
            affiliate = await generate_affiliate_link(final_url)
            if affiliate:
                final_url = affiliate
        except Exception:
            pass  # 변환 실패해도 원본 URL 사용

    deal_data = {
        "title": body.title.strip(),
        "product_url": final_url,
        "sale_price": sale,
        "original_price": orig,
        "discount_rate": dr,
        "image_url": body.image_url.strip(),
        "category": category,
        "source": detected_source,
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


@router.get("/visitors")
async def get_visitors(
    x_admin_key: Optional[str] = Header(None),
    days: int = Query(7, ge=1, le=30),
):
    """IP별 방문·클릭 통계 — 최근 N일"""
    verify_admin(x_admin_key)
    sb = db.get_supabase()
    from datetime import datetime, timedelta, timezone

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    res = sb.table("event_logs") \
        .select("ip_address,event_type,deal_id,session_id,user_agent,created_at") \
        .gte("created_at", since) \
        .not_.is_("ip_address", "null") \
        .order("created_at", desc=True) \
        .limit(5000) \
        .execute()

    rows = res.data or []

    # IP별 집계
    from collections import defaultdict
    ip_stats: dict = defaultdict(lambda: {
        "ip": "",
        "visits": 0,
        "clicks": 0,
        "deal_opens": 0,
        "last_seen": "",
        "first_seen": "",
        "user_agent": "",
        "sessions": set(),
        "deals_clicked": set(),
    })

    for r in rows:
        ip = r.get("ip_address") or "unknown"
        et = r.get("event_type", "")
        s = ip_stats[ip]
        s["ip"] = ip
        s["user_agent"] = r.get("user_agent") or s["user_agent"]
        ts = r.get("created_at", "")
        if not s["last_seen"] or ts > s["last_seen"]:
            s["last_seen"] = ts
        if not s["first_seen"] or ts < s["first_seen"]:
            s["first_seen"] = ts
        if r.get("session_id"):
            s["sessions"].add(r["session_id"])
        if et == "impression":
            s["visits"] += 1
        elif et == "outbound_click":
            s["clicks"] += 1
            if r.get("deal_id"):
                s["deals_clicked"].add(r["deal_id"])
        elif et == "deal_open":
            s["deal_opens"] += 1

    # 직렬화
    result = []
    for ip, s in ip_stats.items():
        ua = s["user_agent"] or ""
        device = "모바일" if "Mobile" in ua else ("봇" if "bot" in ua.lower() else "PC")
        result.append({
            "ip": ip,
            "visits": s["visits"],
            "deal_opens": s["deal_opens"],
            "clicks": s["clicks"],
            "sessions": len(s["sessions"]),
            "deals_clicked": len(s["deals_clicked"]),
            "device": device,
            "first_seen": s["first_seen"],
            "last_seen": s["last_seen"],
            "user_agent": ua[:120],
        })

    # 최근 방문순 정렬
    result.sort(key=lambda x: x["last_seen"], reverse=True)

    # 최근 이벤트 로그 (상세)
    recent_logs = [{
        "ip": r.get("ip_address"),
        "event": r.get("event_type"),
        "deal_id": r.get("deal_id"),
        "time": r.get("created_at"),
        "device": "모바일" if "Mobile" in (r.get("user_agent") or "") else "PC",
    } for r in rows[:100]]

    return {
        "period_days": days,
        "total_ips": len(result),
        "summary": result,
        "recent_logs": recent_logs,
    }


@router.get("/coupang-link")
async def get_coupang_affiliate_link(
    url: str = Query(..., description="쿠팡 상품 URL"),
    x_admin_key: Optional[str] = Header(None),
):
    """쿠팡 URL → 파트너스 추적 링크 변환"""
    verify_admin(x_admin_key)
    from app.services.coupang_partners import generate_affiliate_link, is_coupang_url
    if not is_coupang_url(url):
        raise HTTPException(status_code=400, detail="쿠팡 URL이 아닙니다")
    affiliate_url = await generate_affiliate_link(url)
    if not affiliate_url:
        raise HTTPException(
            status_code=503,
            detail="링크 생성 실패 — 토큰 만료 또는 블랙리스트 상품"
        )
    return {"original_url": url, "affiliate_url": affiliate_url}


class UpdateCoupangToken(BaseModel):
    token: str
    cookie: str = ""


@router.post("/update-coupang-token")
async def update_coupang_token(
    body: UpdateCoupangToken,
    x_admin_key: Optional[str] = Header(None),
):
    """쿠팡 파트너스 xToken 갱신 — DB 저장, 재배포 불필요"""
    verify_admin(x_admin_key)
    from app.services.coupang_partners import update_token, generate_affiliate_link
    ok = await update_token(body.token, body.cookie)
    if not ok:
        raise HTTPException(status_code=500, detail="DB 저장 실패")
    # 테스트 링크 생성으로 토큰 유효성 확인
    test = await generate_affiliate_link("https://www.coupang.com/vp/products/7554201576")
    return {
        "ok": True,
        "message": "토큰 업데이트 완료",
        "test_link": test or "링크 생성 실패 (블랙리스트 또는 토큰 오류)",
    }


@router.post("/reprocess-community-deals")
async def reprocess_community_deals(
    x_admin_key: Optional[str] = Header(None),
):
    """
    pending 상태 커뮤니티 딜 일괄 재처리
    - 식품/일상용품 → expired+[식품금지]
    - 정가 탐지 성공 → active
    - 탐지 실패 → 유지(수동 검토 필요)
    """
    verify_admin(x_admin_key)
    from app.services.community_enricher import is_food_or_daily, lookup_msrp_from_naver
    import app.db_supabase as db

    sb = db.get_supabase()
    res = (
        sb.table("deals")
        .select("id, title, sale_price, category, source")
        .eq("source", "community")
        .eq("status", "pending")
        .execute()
    )
    deals = res.data or []
    results = {"total": len(deals), "food_expired": 0, "activated": 0, "kept_pending": 0}

    for deal in deals:
        deal_id = deal["id"]
        title = deal.get("title", "")
        sale_price = int(deal.get("sale_price") or 0)
        category = deal.get("category", "")

        # 식품 필터
        if is_food_or_daily(title, category):
            sb.table("deals").update({
                "status": "expired",
                "admin_note": "[자동만료] 식품/일상용품 금지 카테고리",
            }).eq("id", deal_id).execute()
            results["food_expired"] += 1
            continue

        # MSRP 탐지
        msrp = await lookup_msrp_from_naver(title, sale_price)
        if msrp and msrp["original_price"] > sale_price and msrp["discount_rate"] >= 5:
            patch = {
                "status": "active",
                "original_price": msrp["original_price"],
                "discount_rate": msrp["discount_rate"],
            }
            if not deal.get("image_url") and msrp.get("image_url"):
                patch["image_url"] = msrp["image_url"]
            sb.table("deals").update(patch).eq("id", deal_id).execute()
            results["activated"] += 1
        else:
            results["kept_pending"] += 1

    return results
