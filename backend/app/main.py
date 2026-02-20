from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.rate_limit import limiter

from app.config import settings
from app.routers import deals, stats, verify
from app.routers import admin as admin_router
from app.scheduler import start_scheduler, stop_scheduler
import app.db_supabase as db


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

# Rate limiter 등록
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(admin_router.router)


# ──────────────────────────────────────────
# 이벤트 수신 엔드포인트
# ──────────────────────────────────────────

class EventPayload(BaseModel):
    event_type: str  # impression | deal_open | outbound_click
    deal_id: Optional[int] = None
    session_id: Optional[str] = None
    referrer: Optional[str] = None


@app.post("/api/events")
async def track_event(payload: EventPayload, request: Request):
    user_agent = request.headers.get("user-agent")
    # Railway는 X-Forwarded-For로 실제 IP 전달
    ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or request.headers.get("x-real-ip")
        or (request.client.host if request.client else None)
    )
    db.log_event(
        event_type=payload.event_type,
        deal_id=payload.deal_id,
        session_id=payload.session_id,
        referrer=payload.referrer,
        user_agent=user_agent,
        ip_address=ip,
    )
    return {"ok": True}


@app.get("/")
async def root():
    return {"message": "정가파괴 API v2 🔥", "docs": "/docs", "db": "Supabase"}


@app.get("/health")
async def health():
    return {"status": "ok"}
