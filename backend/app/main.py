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
    # DB 테이블 생성
    Base.metadata.create_all(bind=engine)
    # APScheduler 시작
    start_scheduler()
    yield
    # 종료 시 스케줄러 중지
    stop_scheduler()




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
