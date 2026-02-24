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
        .select("title,submitter_name,source,discount_rate")
        .in_("status", ["active", "price_changed"])
        .execute()
        .data
    )

    brand_data: dict[str, dict] = {}
    for d in deals:
        brand = d.get("submitter_name") or ""
        if not brand:
            m = re.match(r'^\[([^\]]+)\]', d.get("title", ""))
            brand = m.group(1).strip() if m else ""
        if not brand or brand.lower() in RETAILER_EXCLUDE:
            continue
        if brand not in brand_data:
            brand_data[brand] = {"count": 0, "discount_sum": 0.0}
        brand_data[brand]["count"] += 1
        brand_data[brand]["discount_sum"] += float(d.get("discount_rate") or 0)

    def to_slug(name: str) -> str:
        slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        return slug

    result = []
    for b, v in sorted(brand_data.items(), key=lambda x: -x[1]["count"]):
        slug = to_slug(b)
        if slug:
            avg_dr = round(v["discount_sum"] / v["count"], 1) if v["count"] else 0
            result.append({"brand": b, "slug": slug, "count": v["count"], "avg_discount": avg_dr})

    return result


@router.get("/brands/{slug}/lowest-ever")
async def get_brand_lowest_ever(slug: str):
    """브랜드의 역대 최저 등록 딜 (만료 포함, sale_price 기준 상위 5개)"""
    import re
    sb = db.get_supabase()

    def to_slug(name: str) -> str:
        return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

    # submitter_name 기반으로 브랜드명 찾기
    all_brands_res = (
        sb.table("deals")
        .select("submitter_name,title")
        .in_("status", ["active", "expired", "price_changed"])
        .limit(500)
        .execute()
        .data
    )
    found_brand = None
    for d in all_brands_res:
        brand = d.get("submitter_name") or ""
        if not brand:
            m = re.match(r'^\[([^\]]+)\]', d.get("title", ""))
            brand = m.group(1).strip() if m else ""
        if brand and to_slug(brand) == slug:
            found_brand = brand
            break

    if not found_brand:
        return []

    res = (
        sb.table("deals")
        .select("id,title,sale_price,original_price,discount_rate,image_url,product_url,affiliate_url,source,category,status,submitter_name,created_at,is_hot")
        .ilike("title", f"%{found_brand}%")
        .in_("status", ["active", "expired", "price_changed"])
        .order("sale_price", desc=False)
        .limit(5)
        .execute()
    )
    return [db._to_deal_dict(r) for r in (res.data or [])]


@router.get("/brands/{slug}/top-deals")
async def get_brand_top_deals(slug: str):
    """브랜드 역대 최저가 TOP 10 딜"""
    import re
    sb = db.get_supabase()

    def to_slug(name: str) -> str:
        return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

    # 전체 딜에서 submitter_name 기반으로 브랜드 탐색
    all_deals = (
        sb.table("deals")
        .select("id,title,sale_price,original_price,discount_rate,image_url,product_url,affiliate_url,source,category,status,submitter_name,created_at,is_hot")
        .order("discount_rate", desc=True)
        .limit(500)
        .execute()
        .data
    )

    brand_deals = []
    found_brand = None
    for d in all_deals:
        brand = d.get("submitter_name") or ""
        if not brand:
            m = re.match(r'^\[([^\]]+)\]', d.get("title", ""))
            brand = m.group(1).strip() if m else ""
        if brand and to_slug(brand) == slug:
            found_brand = brand
            brand_deals.append(d)

    if not found_brand:
        return {"brand": None, "deals": []}

    # discount_rate 기준 TOP 10
    top = sorted(brand_deals, key=lambda x: float(x.get("discount_rate") or 0), reverse=True)[:10]

    return {"brand": found_brand, "deals": top}
