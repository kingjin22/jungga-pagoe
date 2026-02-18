from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.database import Base, engine
from app.routers import deals
from app.routers import stats
from app.routers import verify
from app.models import deal as deal_model  # noqa: F401 - DB 테이블 생성용
from app.scheduler import start_scheduler, stop_scheduler


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

    # APScheduler 시작
    start_scheduler()

    yield

    # 종료 시 스케줄러 중지
    stop_scheduler()


async def _seed_mock_data(db):
    """개발용 초기 데이터 (20개)"""
    from app.models.deal import Deal, DealSource, DealCategory, DealStatus

    mock_deals = [
        # === 쿠팡 딜 ===
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
        {
            "title": "[쿠팡로켓] 삼성 갤럭시 S25 울트라 256GB 스마트폰",
            "original_price": 1899000,
            "sale_price": 1399000,
            "discount_rate": 26.3,
            "image_url": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=300",
            "product_url": "https://www.coupang.com/vp/products/sample4",
            "affiliate_url": "https://link.coupang.com/sample4",
            "source": DealSource.COUPANG,
            "category": DealCategory.ELECTRONICS,
            "upvotes": 61,
            "views": 2340,
            "is_hot": True,
        },
        {
            "title": "[쿠팡] 킨들 페이퍼화이트 (16GB, 광고 없음)",
            "original_price": 249000,
            "sale_price": 179000,
            "discount_rate": 28.1,
            "image_url": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=300",
            "product_url": "https://www.coupang.com/vp/products/sample5",
            "affiliate_url": "https://link.coupang.com/sample5",
            "source": DealSource.COUPANG,
            "category": DealCategory.ELECTRONICS,
            "upvotes": 19,
            "views": 412,
            "is_hot": False,
        },
        {
            "title": "[쿠팡] 닌텐도 스위치 OLED 화이트 본체",
            "original_price": 479000,
            "sale_price": 399000,
            "discount_rate": 16.7,
            "image_url": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=300",
            "product_url": "https://www.coupang.com/vp/products/sample6",
            "affiliate_url": "https://link.coupang.com/sample6",
            "source": DealSource.COUPANG,
            "category": DealCategory.ELECTRONICS,
            "upvotes": 38,
            "views": 1560,
            "is_hot": True,
        },
        # === 네이버 딜 ===
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
        {
            "title": "[네이버] 애플 맥북 에어 M3 13인치 8GB/256GB",
            "original_price": 1690000,
            "sale_price": 1290000,
            "discount_rate": 23.7,
            "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=300",
            "product_url": "https://shopping.naver.com/product/sample3",
            "source": DealSource.NAVER,
            "category": DealCategory.ELECTRONICS,
            "upvotes": 43,
            "views": 1890,
            "is_hot": True,
        },
        {
            "title": "[네이버쇼핑] 샤오미 로봇청소기 S20+ 자동 세척",
            "original_price": 450000,
            "sale_price": 189000,
            "discount_rate": 58.0,
            "image_url": "https://images.unsplash.com/photo-1563453392212-326f5e854473?w=300",
            "product_url": "https://shopping.naver.com/product/sample4",
            "source": DealSource.NAVER,
            "category": DealCategory.HOME,
            "upvotes": 67,
            "views": 2100,
            "is_hot": True,
        },
        {
            "title": "[네이버] 아디다스 울트라부스트 22 런닝화",
            "original_price": 230000,
            "sale_price": 109000,
            "discount_rate": 52.6,
            "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300",
            "product_url": "https://shopping.naver.com/product/sample5",
            "source": DealSource.NAVER,
            "category": DealCategory.SPORTS,
            "upvotes": 44,
            "views": 980,
            "is_hot": True,
        },
        {
            "title": "[네이버] 뉴트리디데이 오메가3 180캡슐 12개월분",
            "original_price": 89900,
            "sale_price": 29900,
            "discount_rate": 66.7,
            "image_url": "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?w=300",
            "product_url": "https://shopping.naver.com/product/sample6",
            "source": DealSource.NAVER,
            "category": DealCategory.BEAUTY,
            "upvotes": 29,
            "views": 720,
            "is_hot": True,
        },
        # === 커뮤니티 제보 ===
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
            "is_hot": True,
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
        {
            "title": "[커뮤니티] 무신사 겨울 패딩 특가 - 브랜드 패딩 최대 60%",
            "original_price": 199000,
            "sale_price": 79000,
            "discount_rate": 60.3,
            "image_url": "https://images.unsplash.com/photo-1551698618-1dfe5d97d256?w=300",
            "product_url": "https://www.musinsa.com/sale",
            "source": DealSource.COMMUNITY,
            "category": DealCategory.FASHION,
            "submitter_name": "패션피플",
            "upvotes": 73,
            "views": 2980,
            "is_hot": True,
        },
        {
            "title": "[커뮤니티] 쿠팡 프레시 사과 5kg 특가 (산지직송)",
            "original_price": 39900,
            "sale_price": 17900,
            "discount_rate": 55.1,
            "image_url": "https://images.unsplash.com/photo-1569870499705-504209102861?w=300",
            "product_url": "https://www.coupang.com/vp/products/sample_apple",
            "affiliate_url": "https://link.coupang.com/sample_apple",
            "source": DealSource.COMMUNITY,
            "category": DealCategory.FOOD,
            "submitter_name": "먹방러버",
            "upvotes": 52,
            "views": 1780,
            "is_hot": True,
        },
        {
            "title": "[커뮤니티] 르쿠르제 냄비 세트 4종 (원래 68만원대)",
            "original_price": 680000,
            "sale_price": 259000,
            "discount_rate": 61.9,
            "image_url": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=300",
            "product_url": "https://shopping.naver.com/product/lecreuset",
            "source": DealSource.COMMUNITY,
            "category": DealCategory.HOME,
            "submitter_name": "살림왕",
            "upvotes": 88,
            "views": 3450,
            "is_hot": True,
        },
        {
            "title": "[커뮤니티] 다이슨 에어랩 멀티스타일러 컴플리트 롱",
            "original_price": 699000,
            "sale_price": 499000,
            "discount_rate": 28.6,
            "image_url": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=300",
            "product_url": "https://www.dyson.co.kr/",
            "source": DealSource.COMMUNITY,
            "category": DealCategory.BEAUTY,
            "submitter_name": "뷰티퀸",
            "upvotes": 96,
            "views": 4120,
            "is_hot": True,
        },
        {
            "title": "[커뮤니티] 배스킨라빈스 파인트 아이스크림 반값 이벤트",
            "original_price": 8500,
            "sale_price": 4250,
            "discount_rate": 50.0,
            "image_url": "https://images.unsplash.com/photo-1563805042-7684c019e1cb?w=300",
            "product_url": "https://www.baskinrobbins.co.kr/",
            "source": DealSource.COMMUNITY,
            "category": DealCategory.FOOD,
            "submitter_name": "아이스크림러버",
            "upvotes": 145,
            "views": 6780,
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
app.include_router(stats.router)
app.include_router(verify.router)


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
