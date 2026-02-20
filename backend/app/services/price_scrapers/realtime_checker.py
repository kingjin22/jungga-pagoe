"""
커뮤니티 딜 실시간 유효성 검증기

전략: 네이버 쇼핑 API의 실시간 최저가(lprice)를 가격 오라클로 활용
- 핫딜 소진 → 해당 쇼핑몰 가격 정상화 → 네이버 lprice도 상승
- 커뮤니티 제시가 ≈ 네이버 lprice → 딜 소진 판단

직접 쇼핑몰 스크래핑 대신 Naver API 활용 이유:
- 각 쇼핑몰(지마켓, 11번가, 쿠팡 등) 봇 차단 심각
- Naver Shopping이 이미 실시간 최저가를 집계
- API 공식 제공 → 안정적
"""
import re
import logging
import httpx
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ── 기준 상수 ──────────────────────────────────────────────
# 커뮤니티 가격이 네이버 lprice 대비 이 비율 미만일 때만 유효 딜
DEAL_VALID_THRESHOLD   = 0.92   # 8% 이상 저렴해야 진짜 딜
# 커뮤니티 가격이 naver lprice보다 높으면 → 딜 소진 확실
DEAL_EXPIRED_THRESHOLD = 1.02   # lprice의 102% 이상이면 만료
# 가품 방지: 커뮤니티 가격이 lprice의 이 비율 미만이면 가품 의심
FRAUD_RATIO = 0.15


@dataclass
class PriceCheckResult:
    valid: bool               # 딜 유효 여부
    reason: str               # 판단 근거
    community_price: float    # 커뮤니티 제시 가격
    naver_lprice: float       # 현재 네이버 최저가
    naver_hprice: float       # 현재 네이버 정가
    naver_product_url: str    # 네이버 카탈로그 URL (product_url로 사용)
    image_url: Optional[str]
    discount_vs_hprice: float  # 정가 기준 할인율

    def __bool__(self):
        return self.valid


class RealtimePriceChecker:
    """
    커뮤니티 딜의 현재 유효성을 네이버 실시간 lprice로 검증.

    수집 시점 + 30분 검증 사이클 모두에서 사용.
    """

    def __init__(self, naver_client_id: str, naver_client_secret: str):
        self.client_id = naver_client_id
        self.client_secret = naver_client_secret

    async def check(
        self,
        title: str,
        community_price: float,
        client: Optional[httpx.AsyncClient] = None,
    ) -> PriceCheckResult:
        """
        커뮤니티 딜 실시간 유효성 검증.

        Args:
            title: 커뮤니티 게시글 제목 (검색 쿼리로 사용)
            community_price: 커뮤니티에서 제시한 가격
            client: 재사용 httpx 클라이언트 (없으면 새로 생성)
        """
        query = self._clean_query(title)
        if len(query) < 4:
            return PriceCheckResult(
                valid=False, reason="검색어 추출 실패",
                community_price=community_price, naver_lprice=0,
                naver_hprice=0, naver_product_url="", image_url=None,
                discount_vs_hprice=0,
            )

        naver = await self._search_naver(query, client)
        if not naver:
            return PriceCheckResult(
                valid=False, reason="네이버 검색 결과 없음",
                community_price=community_price, naver_lprice=0,
                naver_hprice=0, naver_product_url="", image_url=None,
                discount_vs_hprice=0,
            )

        lprice = naver["lprice"]
        hprice = naver["hprice"] or lprice
        product_url = naver["product_url"]

        # ── 검증 1: 가품 의심 ──────────────────────────────
        if community_price > 0 and community_price < lprice * FRAUD_RATIO:
            return PriceCheckResult(
                valid=False,
                reason=f"가품 의심: {community_price:,}원 < lprice({lprice:,}) × 15%",
                community_price=community_price, naver_lprice=lprice,
                naver_hprice=hprice, naver_product_url=product_url,
                image_url=naver.get("image_url"), discount_vs_hprice=0,
            )

        # ── 검증 2: 딜 소진 여부 ──────────────────────────
        # 커뮤니티 가격 ≥ 네이버 lprice * 1.02 → 핫딜 소진 (가격 정상화됨)
        if community_price >= lprice * DEAL_EXPIRED_THRESHOLD:
            return PriceCheckResult(
                valid=False,
                reason=f"딜 소진: {community_price:,}원 ≥ 현재 lprice({lprice:,}) — 가격 정상화됨",
                community_price=community_price, naver_lprice=lprice,
                naver_hprice=hprice, naver_product_url=product_url,
                image_url=naver.get("image_url"), discount_vs_hprice=0,
            )

        # ── 검증 3: 실제 할인 확인 ────────────────────────
        # 정가(hprice) 기준 할인율
        ref_price = hprice if hprice > lprice else lprice
        if community_price >= ref_price * DEAL_VALID_THRESHOLD:
            return PriceCheckResult(
                valid=False,
                reason=f"할인율 미달: {community_price:,}원 vs 기준가({ref_price:,}) — 8% 미만",
                community_price=community_price, naver_lprice=lprice,
                naver_hprice=hprice, naver_product_url=product_url,
                image_url=naver.get("image_url"), discount_vs_hprice=0,
            )

        discount_vs_hprice = round((1 - community_price / ref_price) * 100, 1)

        logger.debug(
            f"✅ 딜 유효: {title[:30]} | 커뮤니티={community_price:,} "
            f"lprice={lprice:,} hprice={hprice:,} → -{discount_vs_hprice}%"
        )

        return PriceCheckResult(
            valid=True,
            reason=f"정가({ref_price:,}) 대비 {discount_vs_hprice}% 할인, lprice({lprice:,})보다 저렴",
            community_price=community_price, naver_lprice=lprice,
            naver_hprice=hprice, naver_product_url=product_url,
            image_url=naver.get("image_url"),
            discount_vs_hprice=discount_vs_hprice,
        )

    # ── 30분 재검증: 기존 딜이 아직 유효한가? ─────────────
    async def recheck_existing(
        self, title: str, stored_sale_price: float,
        client: Optional[httpx.AsyncClient] = None,
    ) -> dict:
        """
        이미 저장된 커뮤니티 딜의 현재 유효성 재확인.
        Returns: {action: 'ok'|'expired'|'price_dropped', verified_price}
        """
        result = await self.check(title, stored_sale_price, client)
        if not result.valid:
            return {"action": "expired", "verified_price": result.naver_lprice, "reason": result.reason}
        return {"action": "ok", "verified_price": result.naver_lprice}

    # ── 내부: 네이버 쇼핑 검색 ────────────────────────────
    async def _search_naver(
        self, query: str, client: Optional[httpx.AsyncClient] = None
    ) -> Optional[dict]:
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        try:
            if client:
                r = await client.get(
                    "https://openapi.naver.com/v1/search/shop.json",
                    params={"query": query, "display": 5, "sort": "sim"},
                    headers=headers, timeout=5,
                )
            else:
                async with httpx.AsyncClient(timeout=5) as c:
                    r = await c.get(
                        "https://openapi.naver.com/v1/search/shop.json",
                        params={"query": query, "display": 5, "sort": "sim"},
                        headers=headers,
                    )
            if r.status_code != 200:
                return None
            items = r.json().get("items", [])
            if not items:
                return None

            # 카탈로그(productType=1) 우선
            catalog = next((i for i in items if str(i.get("productType")) == "1"), None)
            item = catalog or items[0]
            product_id = item.get("productId")
            if product_id and str(item.get("productType")) == "1":
                product_url = f"https://search.shopping.naver.com/catalog/{product_id}"
            else:
                product_url = item.get("link", "")

            return {
                "lprice": int(item.get("lprice") or 0),
                "hprice": int(item.get("hprice") or 0),
                "product_url": product_url,
                "image_url": item.get("image"),
                "naver_product_id": str(product_id) if product_id else None,
            }
        except Exception as e:
            logger.debug(f"Naver search error: {e}")
            return None

    @staticmethod
    def _clean_query(title: str) -> str:
        """제목에서 검색어 추출"""
        t = re.sub(r'^\[?[^\]]{2,15}\]?\s*', '', title)  # 앞 [소스] 제거
        t = re.sub(r'\([^)]*\)', '', t)
        t = re.sub(r'\d{1,3}(?:,\d{3})*원|\d+원', '', t)
        t = re.sub(r'\d+만\s*원', '', t)
        t = re.sub(r'\d+개|\d+팩|\d+ml|\d+g|\d+kg|\d+l', '', t, flags=re.I)
        t = re.sub(r'무료?배송?|무배|핫딜|특가|할인|임박', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t[:50]


# ── 편의 함수 ───────────────────────────────────────────────
async def check_community_deal_price(
    title: str,
    community_price: float,
    naver_client_id: str,
    naver_client_secret: str,
    client: Optional[httpx.AsyncClient] = None,
) -> PriceCheckResult:
    """단건 커뮤니티 딜 가격 유효성 검증"""
    checker = RealtimePriceChecker(naver_client_id, naver_client_secret)
    return await checker.check(title, community_price, client)
