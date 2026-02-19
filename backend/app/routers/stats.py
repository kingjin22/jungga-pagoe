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


@router.get("/brands")
async def get_brands():
    """실제 제품 브랜드만 반환 (리테일러/쇼핑몰 제외)"""
    import re
    sb = db.get_supabase()

    # 리테일러 (쇼핑몰) 제외 목록
    RETAILER_EXCLUDE = {
        "쿠팡", "지마켓", "g마켓", "11번가", "옥션", "롯데온", "네이버", "두타온",
        "에픽게임즈", "epic games", "woot", "amazon", "ebay", "costco",
        "coupang", "gmarket", "ssg", "11st",
    }

    deals = (
        sb.table("deals")
        .select("title,submitter_name,source")
        .in_("status", ["active", "price_changed"])
        .execute()
        .data
    )

    brand_counts: dict[str, int] = {}
    for d in deals:
        brand = d.get("submitter_name") or ""
        if not brand:
            m = re.match(r'^\[([^\]]+)\]', d.get("title", ""))
            brand = m.group(1).strip() if m else ""

        if not brand:
            continue
        # 리테일러 제외
        if brand.lower() in RETAILER_EXCLUDE:
            continue
        brand_counts[brand] = brand_counts.get(brand, 0) + 1

    def to_slug(name: str) -> str:
        # 영문/숫자만 슬러그로 (한글 브랜드는 제외)
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        return slug

    result = []
    for b, c in sorted(brand_counts.items(), key=lambda x: -x[1]):
        slug = to_slug(b)
        if slug:  # 슬러그가 있는(영문) 브랜드만 페이지 생성
            result.append({"brand": b, "slug": slug, "count": c})

    return result
