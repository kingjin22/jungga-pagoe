from fastapi import APIRouter
import app.db_supabase as db

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def get_stats():
    return db.get_stats()


@router.get("/categories")
async def get_categories():
    """DB에 실제 존재하는 카테고리 목록 + 딜 수 반환"""
    sb = db.get_supabase()
    res = (
        sb.table("deals")
        .select("category")
        .in_("status", ["active", "price_changed"])
        .execute()
    )
    counts: dict[str, int] = {}
    for row in res.data or []:
        cat = row.get("category") or "기타"
        counts[cat] = counts.get(cat, 0) + 1

    # 딜 많은 순 정렬
    return [
        {"category": cat, "count": cnt}
        for cat, cnt in sorted(counts.items(), key=lambda x: -x[1])
    ]
