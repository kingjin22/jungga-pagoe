"""
Supabase REST API 기반 데이터 레이어
SQLAlchemy 직접 연결 대신 supabase-py 사용 (포트 5432 우회)
"""
from supabase import create_client, Client
from app.config import settings
import math
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

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
    brand: str = None,
) -> dict:
    sb = get_supabase()
    query = sb.table("deals").select("*", count="exact")

    # active만 노출 — price_changed는 가격 불일치 상태라 노출 금지
    query = query.eq("status", "active")

    if category:
        query = query.eq("category", category)
    if source:
        query = query.eq("source", source)
    if hot_only:
        query = query.eq("is_hot", True)
    if search:
        query = query.ilike("title", f"%{search}%")
    if brand:
        # submitter_name 또는 title의 [Brand] 태그로 필터
        query = query.or_(f"submitter_name.ilike.%{brand}%,title.ilike.%[{brand}]%")

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
        new_views = int(current.data[0].get("views", 0)) + 1
        sb.table("deals").update({"views": new_views}).eq("id", deal_id).execute()


def upvote_deal(deal_id: int) -> dict:
    sb = get_supabase()
    current = sb.table("deals").select("upvotes").eq("id", deal_id).limit(1).execute()
    if not current.data:
        return None
    new_upvotes = int(current.data[0].get("upvotes", 0)) + 1
    # 추천 5개 이상 or 현재 이미 HOT이면 HOT 유지
    cur_hot = bool((sb.table("deals").select("is_hot").eq("id", deal_id).limit(1).execute().data or [{}])[0].get("is_hot"))
    is_hot = cur_hot or new_upvotes >= 5
    sb.table("deals").update({"upvotes": new_upvotes, "is_hot": is_hot}).eq("id", deal_id).execute()
    return {"upvotes": new_upvotes, "is_hot": is_hot}


def create_deal(data: dict) -> dict:
    sb = get_supabase()
    # discount_rate 계산
    orig = float(data.get("original_price", 0))
    sale = float(data.get("sale_price", 0))
    if orig > 0 and sale > 0:
        data["discount_rate"] = round((1 - sale / orig) * 100, 1)

    # ══ 철칙 최후 방어선 ══════════════════════════════
    # 무료딜(sale=0)은 예외, 나머지는 정가 > 판매가 필수
    if sale > 0 and orig <= sale:
        raise ValueError(
            f"[철칙위반] original_price({orig}) <= sale_price({sale}) — 저장 거부: {data.get('title','')[:40]}"
        )
    dr = float(data.get("discount_rate", 0))
    if sale > 0 and dr <= 0:
        raise ValueError(
            f"[철칙위반] discount_rate={dr}% — 저장 거부: {data.get('title','')[:40]}"
        )
    # ═══════════════════════════════════════════════

    data.setdefault("status", "active")
    # is_hot: 외부에서 명시하지 않으면 할인율 기준으로 결정 (setdefault 아닌 강제 적용)
    if "is_hot" not in data:
        data["is_hot"] = data.get("discount_rate", 0) >= 30
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


def deal_duplicate_exists(title: str, sale_price: float, tolerance: float = 0.03) -> bool:
    """제목 기준 중복 체크 — 같은 제목이면 최저가 1개만 유지
    
    URL이 달라도 동일 제목의 active 딜이 이미 있으면 중복으로 판단.
    단, 새 딜이 더 싸면(tolerance 초과) 기존 딜을 만료하고 새 딜 허용.
    """
    sb = get_supabase()
    res = (
        sb.table("deals")
        .select("id, sale_price")
        .eq("title", title)
        .in_("status", ["active", "price_changed"])
        .execute()
    )
    if not res.data:
        return False
    for existing in res.data:
        existing_price = float(existing.get("sale_price") or 0)
        if existing_price <= 0:
            continue
        # 새 딜이 5% 이상 싸면 기존 것 만료하고 새 딜 허용
        if sale_price < existing_price * (1 - tolerance):
            sb.table("deals").update({"status": "expired"}).eq("id", existing["id"]).execute()
            return False  # 새 딜(더 싼 것) 저장 허용
        return True  # 기존 딜이 더 싸거나 비슷 → 중복, 저장 거부
    return False


def get_community_deals_for_expiry_check(hours_since_created: int = 1) -> list[dict]:
    """source_post_url이 있는 모든 활성 딜 목록 (원글 만료 감지 대상 — 소스 무관)"""
    import datetime
    cutoff = (datetime.datetime.utcnow() - datetime.timedelta(hours=hours_since_created)).isoformat()
    sb = get_supabase()
    res = (
        sb.table("deals")
        .select("id, title, source_post_url, created_at, source")
        .eq("status", "active")
        .not_.is_("source_post_url", "null")
        .lt("created_at", cutoff)
        .order("created_at", desc=False)
        .limit(200)
        .execute()
    )
    return res.data or []


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

    total = sb.table("deals").select("id", count="exact").eq("status", "active").execute().count or 0
    hot = sb.table("deals").select("id", count="exact").eq("is_hot", True).eq("status", "active").execute().count or 0
    expired = sb.table("deals").select("id", count="exact").eq("status", "expired").execute().count or 0
    price_changed = sb.table("deals").select("id", count="exact").eq("status", "price_changed").execute().count or 0
    today_added = sb.table("deals").select("id", count="exact").gte("created_at", today_utc_start).eq("status", "active").execute().count or 0

    # 평균 할인율
    rates_res = sb.table("deals").select("discount_rate").eq("status", "active").execute()
    rates = [r["discount_rate"] for r in (rates_res.data or []) if r.get("discount_rate")]
    avg_discount = round(sum(rates) / len(rates), 1) if rates else 0.0

    coupang_count = sb.table("deals").select("id", count="exact").eq("source", "coupang").eq("status", "active").execute().count or 0
    naver_count = sb.table("deals").select("id", count="exact").eq("source", "naver").eq("status", "active").execute().count or 0
    community_count = sb.table("deals").select("id", count="exact").eq("source", "community").eq("status", "active").execute().count or 0

    # 오늘 방문자 수 (page_view 이벤트)
    today_utc_end = (today_kst_start + timedelta(days=1)).astimezone(timezone.utc).isoformat()
    try:
        pv_res = sb.table("event_logs").select("id", count="exact") \
            .eq("event_type", "page_view") \
            .gte("created_at", today_utc_start) \
            .lt("created_at", today_utc_end) \
            .execute()
        today_visitors = pv_res.count or 0
    except Exception:
        today_visitors = 0

    # 실제 마지막 가격 검증 시간 (10분 사이클 표시용)
    try:
        lv_res = sb.table("deals").select("last_verified_at") \
            .eq("status", "active") \
            .order("last_verified_at", desc=True) \
            .limit(1).execute()
        last_verified = (lv_res.data or [{}])[0].get("last_verified_at")
    except Exception:
        last_verified = None

    return {
        "total_deals": total,
        "hot_deals": hot,
        "last_updated_at": last_verified,
        "by_source": {"coupang": coupang_count, "naver": naver_count, "community": community_count},
        "today_added": today_added,
        "avg_discount": avg_discount,
        "expired": expired,
        "price_changed": price_changed,
        "today_visitors": today_visitors,
    }


# ───────────────────────────────────────────
# Admin 전용 함수
# ───────────────────────────────────────────

def log_event(
    event_type: str,
    deal_id: Optional[int] = None,
    session_id: Optional[str] = None,
    referrer: Optional[str] = None,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """event_logs 테이블에 이벤트 INSERT"""
    sb = get_supabase()
    try:
        sb.table("event_logs").insert({
            "event_type": event_type,
            "deal_id": deal_id,
            "session_id": session_id,
            "referrer": referrer,
            "user_agent": user_agent,
            "ip_address": ip_address,
        }).execute()
    except Exception:
        pass  # 이벤트 로깅 실패는 무시


def get_admin_metrics(date_str: Optional[str] = None) -> dict:
    """당일 집계 + 최근 7일 추이 + Top10 딜
    최적화: count=exact 쿼리를 ThreadPoolExecutor로 병렬 실행 (8s → ~1s)
    """
    from collections import Counter
    from concurrent.futures import ThreadPoolExecutor, as_completed

    sb = get_supabase()
    KST = timezone(timedelta(hours=9))
    now_kst = datetime.now(KST)

    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=KST)
        except ValueError:
            target_date = now_kst
    else:
        target_date = now_kst

    # 당일 범위
    day_start_kst = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_start_utc = day_start_kst.astimezone(timezone.utc).isoformat()
    day_end_utc = (day_start_kst + timedelta(days=1)).astimezone(timezone.utc).isoformat()
    today_str = day_start_kst.strftime("%Y-%m-%d")

    # 날짜 범위 미리 계산
    day_ranges = []
    for i in range(6, -1, -1):
        d_kst = now_kst - timedelta(days=i)
        d_str = d_kst.strftime("%Y-%m-%d")
        d_start = d_kst.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()
        d_end = (d_kst.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).astimezone(timezone.utc).isoformat()
        day_ranges.append((d_str, d_start, d_end))

    EVENT_TYPES = ["page_view", "impression", "outbound_click", "deal_open"]

    def _count(event_type: str, start: str, end: str) -> int:
        try:
            res = sb.table("event_logs").select("id", count="exact") \
                .eq("event_type", event_type) \
                .gte("created_at", start).lt("created_at", end) \
                .execute()
            return res.count or 0
        except Exception:
            return 0

    # ── 병렬 실행: 최대 20 스레드로 count 쿼리 동시 처리 ──
    tasks: dict = {}
    with ThreadPoolExecutor(max_workers=20) as pool:
        for d_str, d_start, d_end in day_ranges:
            for etype in EVENT_TYPES:
                f = pool.submit(_count, etype, d_start, d_end)
                tasks[f] = (d_str, etype)
        # 딜 수도 병렬
        f_active = pool.submit(lambda: sb.table("deals").select("id", count="exact").eq("status", "active").execute().count or 0)
        f_new = pool.submit(lambda: sb.table("deals").select("id", count="exact").eq("status", "active").gte("created_at", day_start_utc).lt("created_at", day_end_utc).execute().count or 0)
        # Top10 click IDs (오늘 클릭 목록)
        f_clicks = pool.submit(
            lambda: sb.table("event_logs").select("deal_id")
                .eq("event_type", "outbound_click")
                .gte("created_at", day_start_utc).lt("created_at", day_end_utc)
                .limit(5000).execute().data or []
        )

        # 결과 수집
        day_buckets: dict = {d_str: {e: 0 for e in EVENT_TYPES} for d_str, _, _ in day_ranges}
        for f in as_completed(tasks):
            d_str, etype = tasks[f]
            day_buckets[d_str][etype] = f.result()

        active_count = f_active.result()
        new_deals_count = f_new.result()
        top10_raw = f_clicks.result()

    today_b = day_buckets.get(today_str, {e: 0 for e in EVENT_TYPES})
    pv_count = today_b.get("page_view", 0)
    impression_count = today_b.get("impression", 0)
    click_count = today_b.get("outbound_click", 0)
    deal_open_count = today_b.get("deal_open", 0)

    # 7일 트렌드
    trend = [
        {
            "date": d_str,
            "pv": day_buckets[d_str]["page_view"],
            "clicks": day_buckets[d_str]["outbound_click"],
            "deal_opens": day_buckets[d_str]["deal_open"],
        }
        for d_str, _, _ in day_ranges
    ]

    # Top 10 딜
    click_counter: Counter = Counter(e["deal_id"] for e in top10_raw if e.get("deal_id"))
    top10_ids = [did for did, _ in click_counter.most_common(10)]
    top10_deals = []
    if top10_ids:
        deals_res = sb.table("deals") \
            .select("id,title,sale_price,discount_rate,source,upvotes") \
            .in_("id", top10_ids).execute().data or []
        deal_map = {d["id"]: d for d in deals_res}
        for did in top10_ids:
            if did in deal_map:
                d = deal_map[did]
                top10_deals.append({
                    "id": d["id"],
                    "title": d.get("title", ""),
                    "sale_price": float(d.get("sale_price", 0)),
                    "discount_rate": float(d.get("discount_rate", 0)),
                    "source": d.get("source", ""),
                    "upvotes": int(d.get("upvotes", 0)),
                    "clicks_today": click_counter[did],
                })

    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "today": {
            "pv": pv_count,
            "impressions": impression_count,
            "clicks": click_count,
            "deal_opens": deal_open_count,
            "active_deals": active_count,
            "new_deals": new_deals_count,
        },
        "trend": trend,
        "top10": top10_deals,
    }


def get_admin_deals(
    status: Optional[str] = None,
    source: Optional[str] = None,
    search: Optional[str] = None,
    pinned: Optional[bool] = None,
    sort: str = "latest",
    page: int = 1,
    size: int = 30,
) -> dict:
    """관리자용 딜 목록 (모든 status 포함)"""
    sb = get_supabase()
    query = sb.table("deals").select("*", count="exact")

    if status:
        query = query.eq("status", status)
    if source:
        query = query.eq("source", source)
    if search:
        query = query.ilike("title", f"%{search}%")
    if pinned is not None:
        query = query.eq("pinned", pinned)

    sort_map = {
        "latest": ("created_at", False),
        "popular": ("upvotes", False),
        "discount": ("discount_rate", False),
        "views": ("views", False),
        "pinned": ("pinned", False),
    }
    col, asc = sort_map.get(sort, ("created_at", False))
    query = query.order(col, desc=not asc)

    offset = (page - 1) * size
    query = query.range(offset, offset + size - 1)

    res = query.execute()
    total = res.count or 0
    items = res.data or []

    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": math.ceil(total / size) if total > 0 else 1,
    }


def update_deal_admin(deal_id: int, data: Dict[str, Any]) -> Optional[dict]:
    """관리자 필드 업데이트"""
    sb = get_supabase()
    allowed = {
        "status", "pinned", "admin_note", "expires_at", "is_hot",
        "title", "image_url", "category", "sale_price", "original_price",
        "discount_rate", "product_url", "description",
    }
    patch = {k: v for k, v in data.items() if k in allowed and v is not None}
    if not patch:
        return None
    res = sb.table("deals").update(patch).eq("id", deal_id).execute()
    return res.data[0] if res.data else None


def get_deal_admin(deal_id: int) -> Optional[dict]:
    """관리자용 딜 상세 (price_history 포함)"""
    sb = get_supabase()
    deal_res = sb.table("deals").select("*").eq("id", deal_id).limit(1).execute()
    if not deal_res.data:
        return None
    deal = deal_res.data[0]

    # 가격 히스토리
    try:
        ph_res = sb.table("price_history").select("*").eq("deal_id", deal_id).order("checked_at", desc=True).limit(30).execute()
        deal["price_history"] = ph_res.data or []
    except Exception:
        deal["price_history"] = []

    # 집계 (event_logs)
    try:
        KST = timezone(timedelta(hours=9))
        day_start = datetime.now(KST).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc).isoformat()
        ev_res = sb.table("event_logs").select("event_type").eq("deal_id", deal_id).gte("created_at", day_start).execute()
        events = ev_res.data or []
        deal["stats_today"] = {
            "impressions": sum(1 for e in events if e["event_type"] == "page_view"),
            "deal_opens": sum(1 for e in events if e["event_type"] == "deal_open"),
            "clicks": sum(1 for e in events if e["event_type"] == "outbound_click"),
        }
    except Exception:
        deal["stats_today"] = {"impressions": 0, "deal_opens": 0, "clicks": 0}

    return deal
