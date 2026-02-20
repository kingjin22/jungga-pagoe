"""
쿠팡 파트너스 링크 생성 서비스
- COUPANG_PARTNERS_TOKEN 환경변수에 xToken 저장
- /api/v1/url/any 호출 → 파트너스 short URL 반환
"""
import httpx
import os
from urllib.parse import quote
from typing import Optional

PARTNERS_BASE = "https://partners.coupang.com"
TOKEN_ENV = "COUPANG_PARTNERS_TOKEN"
COOKIE_ENV = "COUPANG_PARTNERS_COOKIE"


def get_token() -> Optional[str]:
    return os.environ.get(TOKEN_ENV, "").strip() or None


def get_cookie() -> str:
    return os.environ.get(COOKIE_ENV, "")


async def generate_affiliate_link(coupang_url: str) -> Optional[str]:
    """
    쿠팡 상품 URL → 파트너스 추적 링크 변환
    성공: 'https://link.coupang.com/a/XXXXX'
    실패: None
    """
    token = get_token()
    if not token:
        return None

    encoded = quote(coupang_url, safe="")
    cookie = get_cookie()

    headers = {
        "X-Token": token,
        "Referer": "https://partners.coupang.com/",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }
    if cookie:
        headers["Cookie"] = cookie

    try:
        async with httpx.AsyncClient(base_url=PARTNERS_BASE, timeout=10) as client:
            r = await client.get(
                f"/api/v1/url/any?coupangUrl={encoded}",
                headers=headers,
            )
            j = r.json()
            if j.get("rCode") == "0" and j.get("data", {}).get("shortUrl"):
                return j["data"]["shortUrl"]
            # 블랙리스트(703) or 인증오류(403/401) 로깅
            code = j.get("rCode", "?")
            msg = j.get("rMessage", "")
            if code not in ("703",):  # 703은 상품 이슈, 나머지는 토큰 문제
                import logging
                logging.warning(f"[CoupangPartners] rCode={code} msg={msg}")
            return None
    except Exception as e:
        import logging
        logging.error(f"[CoupangPartners] 링크 생성 오류: {e}")
        return None


def is_coupang_url(url: str) -> bool:
    return any(d in url.lower() for d in ["coupang.com", "coupa.ng"])
