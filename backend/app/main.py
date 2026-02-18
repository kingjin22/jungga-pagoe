from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import Base, engine
from app.routers import deals
from app.models import deal as deal_model  # noqa: F401 - DB 테이블 생성용


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 DB 테이블 생성
    Base.metadata.create_all(bind=engine)

    # 초기 목업 데이터 시드
    from app.database import SessionLocal
    from app.models.deal import Deal, DealSource, DealCategory, DealStatus
    db = SessionLocal()
    try:
        if db.query(Deal).count() == 0:
            await _seed_mock_data(db)
    finally:
        db.close()

    yield


async def _seed_mock_data(db):
    """개발용 초기 데이터"""
    from app.models.deal import Deal, DealSource, DealCategory, DealStatus
    from app.services.coupang import _get_mock_coupang_deals
    from app.services.naver import _get_mock_naver_deals

    mock_deals = [
        # 쿠팡 딜
        {
            "title": "[쿠팡로켓] 삼성 갤럭시 버즈3 프로 무선이어폰 노캔",
            "original_price": 299000,
            "sale_price": 179000,
            "discount_rate": 40.1,
            "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=300",
            "product_url": "https://www.coupang.com/vp/products/sample1",
            "affiliate_url": "https://link.coupang.com/sample1",
            "source": DealSource.COUPANG,
            "category": DealCategory.ELECTRONICS,
            "upvotes": 47,
            "views": 1230,
            "is_hot": True,
        },
        {
            "title": "[쿠팡] 다이슨 V12 Detect Slim 무선청소기",
            "original_price": 899000,
            "sale_price": 599000,
            "discount_rate": 33.4,
            "image_url": "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=300",
            "product_url": "https://www.coupang.com/vp/products/sample2",
            "affiliate_url": "https://link.coupang.com/sample2",
            "source": DealSource.COUPANG,
            "category": DealCategory.HOME,
            "upvotes": 32,
            "views": 890,
            "is_hot": True,
        },
        {
            "title": "[쿠팡] 나이키 에어포스1 07 화이트 운동화",
            "original_price": 139000,
            "sale_price": 79900,
            "discount_rate": 42.5,
            "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300",
            "product_url": "https://www.coupang.com/vp/products/sample3",
            "affiliate_url": "https://link.coupang.com/sample3",
            "source": DealSource.COUPANG,
            "category": DealCategory.SPORTS,
            "upvotes": 28,
            "views": 654,
            "is_hot": True,
        },
        # 네이버 딜
        {
            "title": "[네이버페이특가] 애플 에어팟 프로 2세대 USB-C",
            "original_price": 359000,
            "sale_price": 239000,
            "discount_rate": 33.4,
            "image_url": "https://images.unsplash.com/photo-1603351154351-5e2d0600bb77?w=300",
            "product_url": "https://shopping.naver.com/product/sample1",
            "source": DealSource.NAVER,
            "category": DealCategory.ELECTRONICS,
            "upvotes": 21,
            "views": 445,
            "is_hot": False,
        },
        {
            "title": "[네이버쇼핑] 헝가리 구스다운 패딩 겨울 방한",
            "original_price": 450000,
            "sale_price": 169000,
            "discount_rate": 62.4,
            "image_url": "https://images.unsplash.com/photo-1544923246-77307dd654cb?w=300",
            "product_url": "https://shopping.naver.com/product/sample2",
            "source": DealSource.NAVER,
            "category": DealCategory.FASHION,
            "upvotes": 55,
            "views": 1820,
            "is_hot": True,
        },
        # 커뮤니티 제보
        {
            "title": "GS25 편의점 1+1 삼각김밥 대박 - 어제부터 진행 중",
            "original_price": 2000,
            "sale_price": 1000,
            "discount_rate": 50.0,
            "image_url": "https://images.unsplash.com/photo-1569050467447-ce54b3bbc37d?w=300",
            "product_url": "https://www.gsretail.com/",
            "source": DealSource.COMMUNITY,
            "category": DealCategory.FOOD,
            "submitter_name": "핫딜헌터",
            "upvotes": 89,
            "views": 3210,
            "is_hot": True,
        },
        {
            "title": "올리브영 세일 락토핏 유산균 50% 할인",
            "original_price": 35000,
            "sale_price": 17500,
            "discount_rate": 50.0,
            "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=300",
            "product_url": "https://www.oliveyoung.co.kr/",
            "source": DealSource.COMMUNITY,
            "category": DealCategory.BEAUTY,
            "submitter_name": "딜파인더",
            "upvotes": 34,
            "views": 789,
            "is_hot": False,
        },
        {
            "title": "[커뮤니티제보] 스타벅스 아이스아메리카노 1+1 프로모션 (오늘만)",
            "original_price": 5500,
            "sale_price": 2750,
            "discount_rate": 50.0,
            "image_url": "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?w=300",
            "product_url": "https://www.starbucks.co.kr/",
            "source": DealSource.COMMUNITY,
            "category": DealCategory.FOOD,
            "submitter_name": "카페러버",
            "upvotes": 127,
            "views": 5430,
            "is_hot": True,
        },
    ]

    for d in mock_deals:
        db.add(Deal(**d))
    db.commit()
    print(f"✅ {len(mock_deals)}개 목업 딜 데이터 시드 완료")


app = FastAPI(
    title="정가파괴 API",
    description="쿠팡/네이버 핫딜 + 커뮤니티 제보 딜 수집기",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터
app.include_router(deals.router)


@app.get("/")
async def root():
    return {
        "message": "정가파괴 API 🔥",
        "docs": "/docs",
        "status": "running"
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
