from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.config import settings
from app.routers import deals, stats, verify
from app.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="정가파괴 API",
    description="쿠팡/네이버/뽐뿌 핫딜 + 커뮤니티 제보",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(deals.router)
app.include_router(stats.router)
app.include_router(verify.router)


@app.get("/")
async def root():
    return {"message": "정가파괴 API v2 🔥", "docs": "/docs", "db": "Supabase"}


@app.get("/health")
async def health():
    return {"status": "ok"}
