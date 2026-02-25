"""
C-002: 인기 검색어 API
event_logs 테이블 (event_type='search', referrer=keyword) 기반
"""
from fastapi import APIRouter
from datetime import datetime, timezone, timedelta
from collections import Counter
import app.db_supabase as db

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("/popular")
async def get_popular_searches(limit: int = 10):
    """최근 7일 인기 검색어 TOP N 반환"""
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
        return [
            {"keyword": kw, "count": cnt}
            for kw, cnt in counter.most_common(limit)
            if cnt >= 1
        ]
    except Exception as e:
        return []
