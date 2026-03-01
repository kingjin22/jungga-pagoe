"""
C-002: 인기 검색어 API
event_logs 테이블 (event_type='search', referrer=keyword) 기반
C-024: 키워드별 최고 할인율 + 최저가 포함 (쿠차 스타일)
"""
from fastapi import APIRouter
from datetime import datetime, timezone, timedelta
from collections import Counter
import app.db_supabase as db

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/popular")
async def get_popular_searches(limit: int = 10):
    """최근 7일 인기 검색어 TOP N 반환 (C-024: 할인율+최저가 포함)"""
    sb = db.get_supabase()
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    try:
        res = (
            sb.table("event_logs")
            .select("referrer")
            .eq("event_type", "search")
            .gte("created_at", since)
            .not_.is_("referrer", "null")
            .limit(5000)
            .execute()
        )
        rows = res.data or []
        counter: Counter = Counter(
            r["referrer"].strip().lower()
            for r in rows
            if r.get("referrer") and len(r["referrer"].strip()) >= 1
        )
        top_keywords = [
            (kw, cnt)
            for kw, cnt in counter.most_common(limit)
            if cnt >= 1
        ]

        result = []
        for kw, cnt in top_keywords:
            entry: dict = {
                "keyword": kw,
                "count": cnt,
                "discount_rate": None,
                "min_price": None,
            }
            try:
                deals_res = (
                    sb.table("deals")
                    .select("discount_rate,sale_price")
                    .eq("status", "active")
                    .ilike("title", f"%{kw}%")
                    .gt("discount_rate", 0)
                    .limit(100)
                    .execute()
                )
                deals = deals_res.data or []
                if deals:
                    max_discount = max(
                        (float(d.get("discount_rate") or 0) for d in deals),
                        default=0,
                    )
                    prices = [
                        float(d.get("sale_price") or 0)
                        for d in deals
                        if d.get("sale_price") and float(d.get("sale_price") or 0) > 0
                    ]
                    if max_discount > 0:
                        entry["discount_rate"] = round(max_discount)
                    if prices:
                        entry["min_price"] = round(min(prices))
            except Exception:
                pass
            result.append(entry)

        return result
    except Exception:
        return []
