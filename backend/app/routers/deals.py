from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
import math

from app.database import get_db
from app.models.deal import Deal, DealSource, DealCategory, DealStatus
from app.schemas.deal import DealResponse, DealListResponse, DealCreate, DealSubmitCommunity
from app.services import coupang, naver, ppomppu

router = APIRouter(prefix="/api/deals", tags=["deals"])


def calculate_discount_rate(original: float, sale: float) -> float:
    if original <= 0:
        return 0
    return round((1 - sale / original) * 100, 1)


@router.get("/", response_model=DealListResponse)
async def get_deals(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    category: Optional[DealCategory] = None,
    source: Optional[DealSource] = None,
    sort: str = Query("latest", pattern="^(latest|popular|discount|price_asc|price_desc)$"),
    search: Optional[str] = None,
    hot_only: bool = False,
):
    """딜 목록 조회"""
    # ACTIVE + PRICE_CHANGED 둘 다 표시 (EXPIRED만 숨김)
    query = db.query(Deal).filter(
        Deal.status.in_([DealStatus.ACTIVE, DealStatus.PRICE_CHANGED])
    )

    # 필터
    if category:
        query = query.filter(Deal.category == category)
    if source:
        query = query.filter(Deal.source == source)
    if hot_only:
        query = query.filter(Deal.is_hot == True)
    if search:
        query = query.filter(Deal.title.ilike(f"%{search}%"))

    # 정렬
    if sort == "latest":
        query = query.order_by(Deal.created_at.desc())
    elif sort == "popular":
        query = query.order_by(Deal.upvotes.desc(), Deal.views.desc())
    elif sort == "discount":
        query = query.order_by(Deal.discount_rate.desc())
    elif sort == "price_asc":
        query = query.order_by(Deal.sale_price.asc())
    elif sort == "price_desc":
        query = query.order_by(Deal.sale_price.desc())

    total = query.count()
    offset = (page - 1) * size
    items = query.offset(offset).limit(size).all()

    return DealListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 1,
    )


@router.get("/hot", response_model=list[DealResponse])
async def get_hot_deals(db: Session = Depends(get_db)):
    """핫딜 TOP 10"""
    deals = (
        db.query(Deal)
        .filter(Deal.status == DealStatus.ACTIVE, Deal.is_hot == True)
        .order_by(Deal.upvotes.desc())
        .limit(10)
        .all()
    )
    return deals


@router.get("/{deal_id}", response_model=DealResponse)
async def get_deal(deal_id: int, db: Session = Depends(get_db)):
    """딜 상세 조회"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")

    # 조회수 증가
    deal.views += 1
    db.commit()
    db.refresh(deal)
    return deal


@router.post("/{deal_id}/upvote")
async def upvote_deal(deal_id: int, db: Session = Depends(get_db)):
    """딜 추천"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")

    deal.upvotes += 1
    # 추천 10개 이상이면 핫딜 태그
    if deal.upvotes >= 10:
        deal.is_hot = True
    db.commit()
    return {"upvotes": deal.upvotes, "is_hot": deal.is_hot}


@router.post("/submit", response_model=DealResponse)
async def submit_community_deal(
    deal_data: DealSubmitCommunity,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """커뮤니티 딜 제보"""
    discount_rate = calculate_discount_rate(deal_data.original_price, deal_data.sale_price)

    if discount_rate < 10:
        raise HTTPException(status_code=400, detail="할인율이 10% 이상인 딜만 제보 가능합니다")

    deal = Deal(
        title=deal_data.title,
        description=deal_data.description,
        original_price=deal_data.original_price,
        sale_price=deal_data.sale_price,
        discount_rate=discount_rate,
        image_url=deal_data.image_url,
        product_url=deal_data.product_url,
        category=deal_data.category,
        source=DealSource.COMMUNITY,
        submitter_name=deal_data.submitter_name or "익명",
        status=DealStatus.ACTIVE,
    )

    # 쿠팡 링크면 파트너스 링크 자동 변환 (백그라운드)
    if "coupang.com" in deal_data.product_url:
        background_tasks.add_task(_convert_to_affiliate, deal, db)

    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal


@router.post("/sync/coupang")
async def sync_coupang_deals(db: Session = Depends(get_db)):
    """쿠팡 API에서 딜 동기화 (관리자용)"""
    deals_data = await coupang.get_best_deals(limit=30)
    created = 0

    for item in deals_data:
        # 중복 체크
        existing = db.query(Deal).filter(Deal.product_url == item["product_url"]).first()
        if existing:
            continue

        discount_rate = calculate_discount_rate(item["original_price"], item["sale_price"])
        if discount_rate < 5:
            continue

        deal = Deal(
            title=item["title"],
            original_price=item["original_price"],
            sale_price=item["sale_price"],
            discount_rate=discount_rate,
            image_url=item.get("image_url"),
            product_url=item["product_url"],
            affiliate_url=item.get("affiliate_url"),
            source=DealSource.COUPANG,
            status=DealStatus.ACTIVE,
            is_hot=discount_rate >= 40,
        )
        db.add(deal)
        created += 1

    db.commit()
    return {"synced": created, "message": f"{created}개 쿠팡 딜 동기화 완료"}


@router.post("/sync/naver")
async def sync_naver_deals(db: Session = Depends(get_db)):
    """네이버 API에서 딜 동기화 (관리자용)"""
    deals_data = await naver.collect_real_deals(limit_per_keyword=8)
    created = 0

    for item in deals_data:
        existing = db.query(Deal).filter(Deal.product_url == item["product_url"]).first()
        if existing:
            continue

        discount_rate = calculate_discount_rate(item["original_price"], item["sale_price"])
        if discount_rate < 5:
            continue

        deal = Deal(
            title=item["title"],
            original_price=item["original_price"],
            sale_price=item["sale_price"],
            discount_rate=discount_rate,
            image_url=item.get("image_url"),
            product_url=item["product_url"],
            source=DealSource.NAVER,
            status=DealStatus.ACTIVE,
            is_hot=discount_rate >= 40,
        )
        db.add(deal)
        created += 1

    db.commit()
    return {"synced": created, "message": f"{created}개 네이버 딜 동기화 완료"}


@router.post("/sync/ppomppu")
async def sync_ppomppu_deals(db: Session = Depends(get_db)):
    """뽐뿌 RSS에서 실제 핫딜 동기화"""
    deals_data = await ppomppu.fetch_ppomppu_deals()
    created = 0

    for item in deals_data:
        existing = db.query(Deal).filter(Deal.product_url == item["product_url"]).first()
        if existing:
            continue

        discount_rate = item.get("discount_rate") or calculate_discount_rate(
            item["original_price"], item["sale_price"]
        )
        if discount_rate < 5:
            continue

        category_map = {
            "전자기기": DealCategory.ELECTRONICS,
            "패션": DealCategory.FASHION,
            "식품": DealCategory.FOOD,
            "뷰티": DealCategory.BEAUTY,
            "홈리빙": DealCategory.HOME,
            "스포츠": DealCategory.SPORTS,
            "유아동": DealCategory.KIDS,
        }

        deal = Deal(
            title=item["title"],
            description=item.get("description"),
            original_price=item["original_price"],
            sale_price=item["sale_price"],
            discount_rate=discount_rate,
            image_url=item.get("image_url"),
            product_url=item["product_url"],
            source=DealSource.COMMUNITY,
            category=category_map.get(item.get("category", "기타"), DealCategory.OTHER),
            status=DealStatus.ACTIVE,
            is_hot=discount_rate >= 40,
            submitter_name="뽐뿌",
        )
        db.add(deal)
        created += 1

    db.commit()
    return {"synced": created, "message": f"{created}개 뽐뿌 딜 동기화 완료"}


@router.patch("/{deal_id}/expire")
async def expire_deal(deal_id: int, db: Session = Depends(get_db)):
    """딜 만료 처리"""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")

    deal.status = DealStatus.EXPIRED
    db.commit()
    return {"id": deal_id, "status": "expired", "message": "딜이 만료 처리되었습니다"}


async def _convert_to_affiliate(deal: Deal, db: Session):
    """백그라운드: 쿠팡 파트너스 링크 변환"""
    affiliate_url = await coupang.get_affiliate_link(deal.product_url)
    deal.affiliate_url = affiliate_url
    db.commit()
