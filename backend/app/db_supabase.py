"""
Supabase REST API 기반 데이터 레이어
SQLAlchemy 직접 연결 대신 supabase-py 사용 (포트 5432 우회)
"""
from supabase import create_client, Client
from app.config import settings
import math
from datetime import datetime, timezone

_client = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client


# ───────────────────────────────────────────
# Deal CRUD
# ───────────────────────────────────────────

def _to_deal_dict(row: dict) -> dict:
    """Supabase row → API response dict 정규화"""
    return {
        "id": row.get("id"),
        "title": row.get("title", ""),
        "description": row.get("description"),
        "original_price": float(row.get("original_price", 0)),
        "sale_price": float(row.get("sale_price", 0)),
        "discount_rate": float(row.get("discount_rate", 0)),
        "image_url": row.get("image_url"),
        "product_url": row.get("product_url", ""),
        "affiliate_url": row.get("affiliate_url"),
        "source": row.get("source", "community"),
        "category": row.get("category", "기타"),
        "status": row.get("status", "active"),
        "upvotes": int(row.get("upvotes", 0)),
        "views": int(row.get("views", 0)),
        "is_hot": bool(row.get("is_hot", False)),
        "submitter_name": row.get("submitter_name"),
        "expires_at": row.get("expires_at"),
        "verified_price": row.get("verified_price"),
        "last_verified_at": row.get("last_verified_at"),
        "created_at": row.get("created_at", ""),
        "updated_at": row.get("updated_at", ""),
    }


def get_deals(
    page: int = 1,
    size: int = 20,
    category: str = None,
    source: str = None,
    sort: str = "latest",
    search: str = None,
    hot_only: bool = False,
) -> dict:
    sb = get_supabase()
    query = sb.table("deals").select("*", count="exact")

    # 상태 필터 (EXPIRED 제외)
    query = query.in_("status", ["active", "price_changed"])

    if category:
        query = query.eq("category", category)
    if source:
        query = query.eq("source", source)
    if hot_only:
        query = query.eq("is_hot", True)
    if search:
        query = query.ilike("title", f"%{search}%")

    # 정렬
    sort_map = {
        "latest":     ("created_at", False),
        "popular":    ("upvotes", False),
        "discount":   ("discount_rate", False),
        "price_asc":  ("sale_price", True),
        "price_desc": ("sale_price", False),
    }
    col, asc = sort_map.get(sort, ("created_at", False))
    query = query.order(col, desc=not asc)

    # 페이지네이션
    offset = (page - 1) * size
    query = query.range(offset, offset + size - 1)

    res = query.execute()
    total = res.count or 0
    items = [_to_deal_dict(r) for r in (res.data or [])]

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": math.ceil(total / size) if total > 0 else 1,
    }


def get_hot_deals(limit: int = 10) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("deals")
        .select("*")
        .in_("status", ["active", "price_changed"])
        .eq("is_hot", True)
        .order("upvotes", desc=True)
        .limit(limit)
        .execute()
    )
    return [_to_deal_dict(r) for r in (res.data or [])]


def get_deal_by_id(deal_id: int) -> dict:
    sb = get_supabase()
    res = sb.table("deals").select("*").eq("id", deal_id).limit(1).execute()
    if not res.data:
        return None
    return _to_deal_dict(res.data[0])


def increment_views(deal_id: int) -> None:
    sb = get_supabase()
    # views + 1 (rpc 또는 read-modify-write)
    current = sb.table("deals").select("views").eq("id", deal_id).limit(1).execute()
    if current.data:
        new_views = int(current.data.get("views", 0)) + 1
        sb.table("deals").update({"views": new_views}).eq("id", deal_id).execute()


def upvote_deal(deal_id: int) -> dict:
    sb = get_supabase()
    current = sb.table("deals").select("upvotes").eq("id", deal_id).limit(1).execute()
    if not current.data:
        return None
    new_upvotes = int(current.data.get("upvotes", 0)) + 1
    is_hot = new_upvotes >= 10
    sb.table("deals").update({"upvotes": new_upvotes, "is_hot": is_hot}).eq("id", deal_id).execute()
    return {"upvotes": new_upvotes, "is_hot": is_hot}


def create_deal(data: dict) -> dict:
    sb = get_supabase()
    # discount_rate 계산
    orig = float(data.get("original_price", 0))
    sale = float(data.get("sale_price", 0))
    if orig > 0 and sale > 0:
        data["discount_rate"] = round((1 - sale / orig) * 100, 1)
    data.setdefault("status", "active")
    data.setdefault("is_hot", data.get("discount_rate", 0) >= 40)
    res = sb.table("deals").insert(data).execute()
    return _to_deal_dict(res.data[0])


def deal_url_exists(product_url: str) -> bool:
    sb = get_supabase()
    res = (
        sb.table("deals")
        .select("id", count="exact")
        .eq("product_url", product_url)
        .execute()
    )
    return (res.count or 0) > 0


def expire_deal(deal_id: int) -> dict:
    sb = get_supabase()
    res = (
        sb.table("deals")
        .update({"status": "expired"})
        .eq("id", deal_id)
        .execute()
    )
    return res.data[0] if res.data else None


def update_deal_verify(deal_id: int, patch: dict) -> None:
    sb = get_supabase()
    sb.table("deals").update(patch).eq("id", deal_id).execute()


def get_deals_for_verify(cutoff_iso: str) -> list[dict]:
    """가격 검증 대상 딜 목록"""
    sb = get_supabase()
    res = (
        sb.table("deals")
        .select("*")
        .in_("status", ["active", "price_changed"])
        .or_(f"last_verified_at.is.null,last_verified_at.lt.{cutoff_iso}")
        .execute()
    )
    return [_to_deal_dict(r) for r in (res.data or [])]


def get_stats() -> dict:
    sb = get_supabase()
    from datetime import datetime, timezone, timedelta
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST)
    # KST 오늘 00:00 → UTC 변환
    today_kst_start = now_kst.replace(hour=0, minute=0, second=0, microsecond=0)
    today_utc_start = today_kst_start.astimezone(timezone.utc).isoformat()

    total = sb.table("deals").select("id", count="exact").execute().count or 0
    hot = sb.table("deals").select("id", count="exact").eq("is_hot", True).in_("status", ["active", "price_changed"]).execute().count or 0
    expired = sb.table("deals").select("id", count="exact").eq("status", "expired").execute().count or 0
    price_changed = sb.table("deals").select("id", count="exact").eq("status", "price_changed").execute().count or 0
    today_added = sb.table("deals").select("id", count="exact").gte("created_at", today_utc_start).execute().count or 0

    # 평균 할인율
    rates_res = sb.table("deals").select("discount_rate").in_("status", ["active", "price_changed"]).execute()
    rates = [r["discount_rate"] for r in (rates_res.data or []) if r.get("discount_rate")]
    avg_discount = round(sum(rates) / len(rates), 1) if rates else 0.0

    coupang_count = sb.table("deals").select("id", count="exact").eq("source", "coupang").execute().count or 0
    naver_count = sb.table("deals").select("id", count="exact").eq("source", "naver").execute().count or 0
    community_count = sb.table("deals").select("id", count="exact").eq("source", "community").execute().count or 0

    return {
        "total_deals": total,
        "hot_deals": hot,
        "by_source": {"coupang": coupang_count, "naver": naver_count, "community": community_count},
        "today_added": today_added,
        "avg_discount": avg_discount,
        "expired": expired,
        "price_changed": price_changed,
    }
