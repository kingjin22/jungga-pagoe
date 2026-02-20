"""
쿠팡 파트너스 링크 생성 서비스
우선순위: Supabase site_settings > 환경변수
- 토큰 갱신: POST /admin/update-coupang-token  
"""
import httpx
import os
from urllib.parse import quote
from typing import Optional
import logging

logger = logging.getLogger(__name__)

PARTNERS_BASE = "https://partners.coupang.com"
_token_cache: dict = {}  # {"token": str, "cookie": str}


async def _fetch_token_from_db() -> tuple[str, str]:
    """Supabase site_settings에서 토큰 조회"""
    try:
        from app.db_supabase import get_supabase
        sb = get_supabase()
        rows = sb.table("site_settings").select("key,value").in_(
            "key", ["coupang_partners_token", "coupang_partners_cookie"]
        ).execute()
        data = {r["key"]: r["value"] for r in (rows.data or [])}
        token = data.get("coupang_partners_token", "").strip()
        cookie = data.get("coupang_partners_cookie", "").strip()
        return token, cookie
    except Exception as e:
        logger.warning(f"[CoupangPartners] DB 토큰 조회 실패: {e}")
        return "", ""


async def get_credentials() -> tuple[str, str]:
    """토큰+쿠키 반환. DB 우선, 없으면 환경변수"""
    # 캐시 사용 (5분 이내)
    import time
    cached_at = _token_cache.get("cached_at", 0)
    if time.time() - cached_at < 300:
        return _token_cache.get("token", ""), _token_cache.get("cookie", "")

    token, cookie = await _fetch_token_from_db()

    if not token:
        token = os.environ.get("COUPANG_PARTNERS_TOKEN", "").strip()
    if not cookie:
        cookie = os.environ.get("COUPANG_PARTNERS_COOKIE", "").strip()

    _token_cache.update({"token": token, "cookie": cookie, "cached_at": time.time()})
    return token, cookie


async def update_token(token: str, cookie: str = "") -> bool:
    """Supabase에 토큰 업데이트 + 캐시 초기화"""
    try:
        from app.db_supabase import get_supabase
        sb = get_supabase()
        sb.table("site_settings").upsert([
            {"key": "coupang_partners_token", "value": token},
            {"key": "coupang_partners_cookie", "value": cookie},
        ]).execute()
        _token_cache.clear()  # 캐시 무효화
        logger.info("[CoupangPartners] 토큰 업데이트 완료")
        return True
    except Exception as e:
        logger.error(f"[CoupangPartners] 토큰 업데이트 실패: {e}")
        return False


async def generate_affiliate_link(coupang_url: str) -> Optional[str]:
    """
    쿠팡 상품 URL → 파트너스 추적 링크 변환
    성공: 'https://link.coupang.com/a/XXXXX'
    실패: None
    """
    token, cookie = await get_credentials()
    if not token:
        logger.warning("[CoupangPartners] 토큰 없음 — Railway Variables 또는 /admin/update-coupang-token 필요")
        return None

    encoded = quote(coupang_url, safe="")

    # AFATK 쿠키 = xToken 값 (동일) → 자동 추가
    if "AFATK=" not in cookie:
        cookie = f"AFATK={token}; {cookie}".strip("; ")

    headers = {
        "X-Token": token,
        "Referer": "https://partners.coupang.com/",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Cookie": cookie,
    }

    try:
        async with httpx.AsyncClient(base_url=PARTNERS_BASE, timeout=10) as client:
            r = await client.get(
                f"/api/v1/url/any?coupangUrl={encoded}",
                headers=headers,
            )
            j = r.json()
            rcode = j.get("rCode", "?")
            if rcode == "0" and j.get("data", {}).get("shortUrl"):
                return j["data"]["shortUrl"]
            # 토큰 만료 감지 → 캐시 무효화
            if rcode in ("401", "403") or r.status_code in (401, 403):
                _token_cache.clear()
                logger.warning("[CoupangPartners] 토큰 만료 — /admin/update-coupang-token으로 갱신 필요")
            elif rcode != "703":
                logger.warning(f"[CoupangPartners] rCode={rcode} msg={j.get('rMessage','')}")
            return None
    except Exception as e:
        logger.error(f"[CoupangPartners] 링크 생성 오류: {e}")
        return None


def is_coupang_url(url: str) -> bool:
    return any(d in url.lower() for d in ["coupang.com", "coupa.ng"])
