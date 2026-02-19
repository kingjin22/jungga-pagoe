from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import Optional
from app.schemas.deal import DealSubmitCommunity, DealResponse, DealListResponse
import app.db_supabase as db

router = APIRouter(prefix="/api/deals", tags=["deals"])


@router.get("/", response_model=DealListResponse)
async def get_deals(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    source: Optional[str] = None,
    sort: str = Query("latest", pattern="^(latest|popular|discount|price_asc|price_desc)$"),
    search: Optional[str] = None,
    hot_only: bool = False,
    brand: Optional[str] = None,
):
    return db.get_deals(
        page=page, size=size, category=category,
        source=source, sort=sort, search=search, hot_only=hot_only,
        brand=brand,
    )


@router.get("/hot")
async def get_hot_deals():
    return db.get_hot_deals(limit=10)


@router.get("/{deal_id}")
async def get_deal(deal_id: int):
    deal = db.get_deal_by_id(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")
    db.increment_views(deal_id)
    deal["views"] += 1

    # 가격 히스토리 + 신뢰지수 (네이버 소스만)
    if deal.get("source") == "naver":
        try:
            from app.services.price_history import get_price_stats, calc_trust_score
            import re
            sb = db.get_supabase()
            # brand: submitter_name 또는 title의 [Brand] 태그에서 추출
            brand = deal.get("submitter_name") or ""
            if not brand:
                m = re.match(r'^\[([^\]]+)\]', deal.get("title", ""))
                brand = m.group(1) if m else ""
            query = re.sub(r'^\[[^\]]+\]\s*', '', deal.get("title", ""))
            stats = get_price_stats(sb, brand, query)
            trust = calc_trust_score(
                int(deal.get("sale_price", 0)),
                stats,
                int(deal.get("original_price", 0))
            )
            deal["price_stats"] = stats
            deal["trust"] = trust
        except Exception:
            pass

    return deal


@router.post("/{deal_id}/upvote")
async def upvote_deal(deal_id: int):
    result = db.upvote_deal(deal_id)
    if not result:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")
    return result


@router.post("/submit")
async def submit_community_deal(
    deal_data: DealSubmitCommunity,
    background_tasks: BackgroundTasks,
):
    orig = deal_data.original_price
    sale = deal_data.sale_price
    discount_rate = round((1 - sale / orig) * 100, 1) if orig > 0 else 0

    if discount_rate < 10:
        raise HTTPException(status_code=400, detail="할인율이 10% 이상인 딜만 제보 가능합니다")

    from app.services.categorizer import infer_category
    category = deal_data.category or infer_category(deal_data.title)

    payload = {
        "title": deal_data.title,
        "description": deal_data.description,
        "original_price": orig,
        "sale_price": sale,
        "discount_rate": discount_rate,
        "image_url": deal_data.image_url,
        "product_url": deal_data.product_url,
        "category": category,
        "source": "community",
        "submitter_name": deal_data.submitter_name or "익명",
        "status": "active",
        "is_hot": discount_rate >= 40,
    }

    # 쿠팡 링크면 파트너스 링크 변환 (백그라운드)
    if "coupang.com" in deal_data.product_url:
        background_tasks.add_task(_convert_to_affiliate_bg, deal_data.product_url, payload)
    
    return db.create_deal(payload)


@router.patch("/{deal_id}/expire")
async def expire_deal(deal_id: int):
    result = db.expire_deal(deal_id)
    if not result:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")
    return {"id": deal_id, "status": "expired"}


@router.post("/sync/naver")
async def sync_naver_deals():
    from app.services.naver import collect_real_deals
    deals_data = await collect_real_deals(limit_per_keyword=8)
    created = 0
    for item in deals_data:
        if db.deal_url_exists(item["product_url"]):
            continue
        orig = item.get("original_price", 0)
        sale = item.get("sale_price", 0)
        if orig <= 0 or sale <= 0:
            continue
        discount_rate = round((1 - sale / orig) * 100, 1)
        if discount_rate < 10:
            continue
        db.create_deal({
            "title": item["title"],
            "original_price": orig,
            "sale_price": sale,
            "discount_rate": discount_rate,
            "image_url": item.get("image_url"),
            "product_url": item["product_url"],
            "source": "naver",
            "category": item.get("category", "기타"),
            "status": "active",
            "is_hot": discount_rate >= 40,
        })
        created += 1
    return {"synced": created, "message": f"{created}개 네이버 딜 동기화 완료"}


@router.post("/sync/ppomppu")
async def sync_ppomppu_deals():
    from app.services.ppomppu import fetch_ppomppu_deals
    deals_data = await fetch_ppomppu_deals()
    created = 0
    for item in deals_data:
        if db.deal_url_exists(item["product_url"]):
            continue
        orig = item.get("original_price", 0)
        sale = item.get("sale_price", 0)
        if orig <= 0 or sale <= 0:
            continue
        discount_rate = item.get("discount_rate") or round((1 - sale / orig) * 100, 1)
        if discount_rate < 5:
            continue
        db.create_deal({
            "title": item["title"],
            "description": item.get("description"),
            "original_price": orig,
            "sale_price": sale,
            "discount_rate": discount_rate,
            "image_url": item.get("image_url"),
            "product_url": item["product_url"],
            "source": "community",
            "category": item.get("category", "기타"),
            "status": "active",
            "is_hot": discount_rate >= 40,
            "submitter_name": "뽐뿌",
        })
        created += 1
    return {"synced": created, "message": f"{created}개 뽐뿌 딜 동기화 완료"}


@router.post("/sync/coupang")
async def sync_coupang_deals():
    from app.services.coupang import get_best_deals
    deals_data = await get_best_deals(limit=30)
    created = 0
    for item in deals_data:
        if db.deal_url_exists(item["product_url"]):
            continue
        orig = item.get("original_price", 0)
        sale = item.get("sale_price", 0)
        if orig <= 0 or sale <= 0:
            continue
        discount_rate = round((1 - sale / orig) * 100, 1)
        if discount_rate < 5:
            continue
        db.create_deal({
            "title": item["title"],
            "original_price": orig,
            "sale_price": sale,
            "discount_rate": discount_rate,
            "image_url": item.get("image_url"),
            "product_url": item["product_url"],
            "affiliate_url": item.get("affiliate_url"),
            "source": "coupang",
            "status": "active",
            "is_hot": discount_rate >= 40,
        })
        created += 1
    return {"synced": created, "message": f"{created}개 쿠팡 딜 동기화 완료"}


async def _convert_to_affiliate_bg(product_url: str, payload: dict):
    from app.services.coupang import get_affiliate_link
    affiliate_url = await get_affiliate_link(product_url)
    if affiliate_url and affiliate_url != product_url:
        # 방금 생성된 딜의 affiliate_url 업데이트
        sb = db.get_supabase()
        sb.table("deals").update({"affiliate_url": affiliate_url}).eq("product_url", product_url).execute()


@router.post("/{deal_id}/report")
async def report_deal(deal_id: int):
    """가격 오류 신고 — 3회 이상 신고 시 자동 숨김"""
    from fastapi import HTTPException
    sb = db.get_supabase()
    try:
        deal = sb.table("deals").select("id,report_count,status").eq("id", deal_id).limit(1).execute().data
    except Exception:
        deal = sb.table("deals").select("id,status").eq("id", deal_id).limit(1).execute().data

    if not deal:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")

    current = deal[0]
    new_count = (current.get("report_count") or 0) + 1
    patch = {}
    try:
        patch["report_count"] = new_count
    except Exception:
        pass

    if new_count >= 3:
        patch["status"] = "expired"

    if patch:
        try:
            sb.table("deals").update(patch).eq("id", deal_id).execute()
        except Exception:
            # report_count 컬럼 없을 경우 status만 업데이트
            if "status" in patch:
                sb.table("deals").update({"status": patch["status"]}).eq("id", deal_id).execute()

    return {"reported": True, "report_count": new_count, "hidden": new_count >= 3}
