"""
가격 검증 서비스 (Price Verifier)

등록된 딜의 실제 현재 가격을 주기적으로 체크하여:
- 가격이 10% 이상 올랐으면 → PRICE_CHANGED
- 가격이 20% 이상 올랐거나 URL이 죽었으면 → EXPIRED
- 가격이 여전히 유효하면 → verified_price, last_verified_at 업데이트
"""
import httpx
import re
from datetime import datetime, timezone
from typing import Optional

from app.config import settings


PRICE_CHANGE_THRESHOLD = 0.10    # 10% 이상 오르면 "가격변동" 표시
EXPIRE_THRESHOLD = 0.20          # 20% 이상 오르면 자동 만료
MAX_FAIL_COUNT = 3               # 연속 3번 실패 시 만료 처리


async def check_naver_price(title: str, registered_price: float) -> Optional[float]:
    """
    네이버 쇼핑 API로 현재 최저가 조회
    유사 상품 중 가장 가까운 가격 반환
    """
    if not settings.NAVER_CLIENT_ID:
        return None

    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }

    # 제목에서 핵심 키워드 추출 (괄호, 특수문자 제거)
    clean_title = re.sub(r"[\[\]()【】\{\}]", " ", title)
    clean_title = re.sub(r"\s+", " ", clean_title).strip()
    # 앞 30자만 사용 (핵심 키워드 위주)
    search_query = clean_title[:40]

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                "https://openapi.naver.com/v1/search/shop.json",
                headers=headers,
                params={
                    "query": search_query,
                    "display": 10,
                    "sort": "asc",  # 가격 낮은순
                },
                timeout=8.0,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])

            if not items:
                return None

            # 등록 가격과 가장 가까운 상품의 최저가 반환
            prices = [int(item.get("lprice", 0)) for item in items if item.get("lprice")]
            if not prices:
                return None

            # 등록 가격의 50%~200% 범위 내 가격만 유효한 것으로 판단
            valid_prices = [
                p for p in prices
                if registered_price * 0.5 <= p <= registered_price * 2.0
            ]

            if not valid_prices:
                return None

            return float(min(valid_prices))  # 최저가 반환

        except Exception as e:
            print(f"  [가격체크] 네이버 API 오류: {e}")
            return None


async def check_url_alive(url: str) -> bool:
    """URL이 살아있는지 HTTP HEAD 요청으로 확인"""
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.head(
                url,
                timeout=5.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; PriceBot/1.0)"},
            )
            return resp.status_code < 400
        except Exception:
            return False


def evaluate_price_change(
    registered_price: float,
    current_price: float,
) -> dict:
    """
    가격 변동 평가
    Returns: {action: "ok" | "price_changed" | "expired", change_pct: float}
    """
    if registered_price <= 0:
        return {"action": "ok", "change_pct": 0.0}

    change_pct = (current_price - registered_price) / registered_price  # 양수면 가격 오름

    if change_pct >= EXPIRE_THRESHOLD:
        return {"action": "expired", "change_pct": round(change_pct * 100, 1)}
    elif change_pct >= PRICE_CHANGE_THRESHOLD:
        return {"action": "price_changed", "change_pct": round(change_pct * 100, 1)}
    elif change_pct < -0.05:
        # 5% 이상 더 떨어짐 → 여전히 유효하고 더 좋은 딜
        return {"action": "ok", "change_pct": round(change_pct * 100, 1)}
    else:
        return {"action": "ok", "change_pct": round(change_pct * 100, 1)}


async def verify_deal(deal) -> dict:
    """
    단일 딜 가격 검증
    Returns: {verified_price, action, change_pct, url_alive}
    """
    print(f"  [검증] #{deal.id} {deal.title[:40]}")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    result = {
        "verified_price": deal.verified_price,
        "last_verified_at": now,
        "action": "ok",
        "change_pct": 0.0,
        "url_alive": True,
    }

    # 1. URL 생존 확인
    url_alive = await check_url_alive(deal.product_url)
    result["url_alive"] = url_alive

    if not url_alive:
        print(f"    → URL 죽음 (fail_count: {deal.verify_fail_count + 1})")
        result["action"] = "url_dead"
        return result

    # 2. 가격 확인 (네이버 소스이거나 제목으로 검색 가능한 경우)
    current_price = None

    if deal.source in ("naver", "community"):
        current_price = await check_naver_price(deal.title, deal.sale_price)
    # 쿠팡은 API 키 필요 → 현재는 URL 생존 여부만 체크

    if current_price is not None:
        result["verified_price"] = current_price
        evaluation = evaluate_price_change(deal.sale_price, current_price)
        result["action"] = evaluation["action"]
        result["change_pct"] = evaluation["change_pct"]
        print(f"    → 현재가: {int(current_price):,}원 (등록가 {int(deal.sale_price):,}원, {evaluation['change_pct']:+.1f}%) → {evaluation['action']}")
    else:
        # 가격 확인 불가 → URL만 살아있으면 OK
        print(f"    → 가격 확인 불가, URL은 정상")

    return result
