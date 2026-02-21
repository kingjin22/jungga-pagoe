"""
상품 URL에서 제목/정가/판매가/이미지 자동 파싱
지원: 쿠팡, 네이버스마트스토어, G마켓, 11번가, 옥션, 일반 OG/JSON-LD
"""
import re
import json
import logging
import httpx
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


@dataclass
class ParsedProduct:
    title: str = ""
    sale_price: Optional[int] = None
    original_price: Optional[int] = None
    discount_rate: Optional[float] = None
    image_url: str = ""
    source: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "sale_price": self.sale_price,
            "original_price": self.original_price,
            "discount_rate": self.discount_rate,
            "image_url": self.image_url,
            "source": self.source,
            "error": self.error,
        }


def _parse_price(text: str) -> Optional[int]:
    """'11,990원' 또는 '11990' → 11990"""
    if not text:
        return None
    nums = re.sub(r"[^\d]", "", str(text))
    return int(nums) if nums else None


def _clean_title(title: str) -> str:
    """HTML 엔티티, 연속 공백 제거"""
    import html
    title = html.unescape(title or "")
    title = re.sub(r"\s+", " ", title).strip()
    # 쿠팡 등 사이트명 suffix 제거
    for suffix in [" - 쿠팡", " | 쿠팡", " - 네이버쇼핑", " | Coupang"]:
        title = title.replace(suffix, "")
    return title.strip()


def _extract_json_ld(html: str) -> dict:
    """JSON-LD Product 스키마 추출"""
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE
    ):
        try:
            data = json.loads(m.group(1))
            if isinstance(data, list):
                data = data[0]
            if data.get("@type") in ("Product", "product"):
                return data
            # BreadcrumbList 안에 있을 수도
            if data.get("@type") == "WebPage":
                for item in data.get("mainEntity", []):
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        return item
        except Exception:
            pass
    return {}


def _extract_og(html: str) -> dict:
    """OpenGraph 메타태그 추출"""
    result = {}
    for m in re.finditer(r'<meta[^>]+property=["\']og:([^"\']+)["\'][^>]+content=["\']([^"\']*)["\']', html, re.IGNORECASE):
        result[m.group(1)] = m.group(2)
    for m in re.finditer(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]+property=["\']og:([^"\']+)["\']', html, re.IGNORECASE):
        result[m.group(2)] = m.group(1)
    return result


async def _parse_coupang_partners(url: str) -> ParsedProduct:
    """
    쿠팡은 Akamai로 직접 파싱 차단 →
    1) Partners API (xToken 있을 때) 우선
    2) Naver Shopping 검색 fallback
    """
    result = ParsedProduct(source="coupang")

    # 1) Partners API — xToken Supabase에서 조회
    try:
        from app.services.coupang_partners import get_coupang_token
        xtoken = await get_coupang_token()
        if xtoken:
            encoded = httpx.URL(url).__str__()
            api_url = f"https://partners.coupang.com/api/v1/url/any?coupangUrl={httpx.URL(url)}"
            async with httpx.AsyncClient(timeout=8, headers={"X-Token": xtoken}) as client:
                r = await client.get(api_url)
                if r.status_code == 200:
                    data = r.json()
                    # partners API는 shortUrl만 반환 → productId로 상품 API 호출
                    short_url = data.get("data", {}).get("shortUrl", "")
                    result.description = short_url  # partners 링크 저장
    except Exception:
        pass

    # URL에서 productId 추출
    m = re.search(r"/products/(\d+)", url)
    product_id = m.group(1) if m else None

    # 2) Naver Shopping API로 쿠팡 상품 검색 (productId 기반)
    # → 쿠팡 상품명을 모르므로 Naver 결과로 대체
    # productId는 힌트로만 사용
    if product_id:
        result.description = f"쿠팡 상품 #{product_id}"
    result.error = "쿠팡은 자동 파싱이 제한됩니다 — 제목/가격을 직접 입력하거나 Naver 검색을 이용하세요"
    return result


async def _parse_coupang(html: str, url: str) -> ParsedProduct:
    """쿠팡 상품 페이지 HTML 파싱 (Akamai 미차단 시)"""
    result = ParsedProduct(source="coupang")

    ld = _extract_json_ld(html)
    if ld.get("name"):
        result.title = _clean_title(ld["name"])
    og = _extract_og(html)
    if not result.title:
        result.title = _clean_title(og.get("title", ""))
    if og.get("image"):
        result.image_url = og["image"]

    orig_m = re.search(r'"originPrice"\s*:\s*(\d+)', html)
    if orig_m:
        result.original_price = _parse_price(orig_m.group(1))
    sale_m = re.search(r'"finalPrice"\s*:\s*(\d+)|"priceValue"\s*:\s*"?(\d+)"?', html)
    if sale_m:
        result.sale_price = _parse_price(next(g for g in sale_m.groups() if g))
    dr_m = re.search(r'"discountRate"\s*:\s*(\d+)', html)
    if dr_m:
        result.discount_rate = float(dr_m.group(1))
    img_m = re.search(r'"mainImageUrl"\s*:\s*"([^"]+)"', html)
    if img_m:
        result.image_url = img_m.group(1)

    if not result.title:
        t_m = re.search(r'<title>([^<]+)</title>', html)
        if t_m:
            result.title = _clean_title(t_m.group(1))

    return result


async def _parse_naver(html: str, url: str) -> ParsedProduct:
    """네이버 스마트스토어/쇼핑 상품 파싱"""
    result = ParsedProduct(source="naver")

    # JSON-LD
    ld = _extract_json_ld(html)
    if ld.get("name"):
        result.title = _clean_title(ld["name"])
    offers = ld.get("offers", {})
    if isinstance(offers, list):
        offers = offers[0]
    if offers.get("price"):
        result.sale_price = _parse_price(str(offers["price"]))

    # OG
    og = _extract_og(html)
    if not result.title and og.get("title"):
        result.title = _clean_title(og.get("title", ""))
    if og.get("image"):
        result.image_url = og["image"]

    # 스마트스토어 특유 패턴
    orig_m = re.search(r'"benefitPrice"\s*:\s*(\d+)|"consumerPrice"\s*:\s*(\d+)|"originalPrice"\s*:\s*(\d+)', html)
    if orig_m:
        result.original_price = _parse_price(next(g for g in orig_m.groups() if g))

    sale_m = re.search(r'"salePrice"\s*:\s*(\d+)|"discountedSalePrice"\s*:\s*(\d+)', html)
    if sale_m:
        result.sale_price = _parse_price(next(g for g in sale_m.groups() if g))

    dr_m = re.search(r'"discountRate"\s*:\s*(\d+)', html)
    if dr_m:
        result.discount_rate = float(dr_m.group(1))

    return result


async def _parse_gmarket(html: str, url: str) -> ParsedProduct:
    """G마켓/옥션 공통 파싱"""
    result = ParsedProduct(source="gmarket" if "gmarket" in url else "auction")
    og = _extract_og(html)
    result.title = _clean_title(og.get("title", ""))
    result.image_url = og.get("image", "")

    orig_m = re.search(r'"price"\s*:\s*"?([0-9,]+)"?', html)
    if orig_m:
        result.original_price = _parse_price(orig_m.group(1))
    sale_m = re.search(r'(?:sale|discount|sell)[_\-]?price["\s:]+["\s]*([0-9,]+)', html, re.IGNORECASE)
    if sale_m:
        result.sale_price = _parse_price(sale_m.group(1))

    return result


async def parse_product_url(url: str) -> ParsedProduct:
    """
    URL에서 상품 정보 자동 파싱
    지원: 쿠팡, 네이버, G마켓, 옥션, 11번가 + 일반 fallback
    """
    url = url.strip()
    if not url.startswith("http"):
        return ParsedProduct(error="올바른 URL을 입력하세요")

    # 쿠팡은 Akamai 차단 → Partners API fallback 먼저
    u_lower = url.lower()
    if "coupang.com" in u_lower or "coupa.ng" in u_lower:
        return await _parse_coupang_partners(url)

    try:
        async with httpx.AsyncClient(
            timeout=12,
            headers=HEADERS,
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
            if r.status_code != 200:
                return ParsedProduct(error=f"페이지 접근 실패 ({r.status_code})")
            html = r.text
            final_url = str(r.url)
    except Exception as e:
        return ParsedProduct(error=f"네트워크 오류: {str(e)[:50]}")

    # 라우팅
    u = final_url.lower()
    if "coupang.com" in u or "coupa.ng" in u:
        result = await _parse_coupang(html, final_url)
    elif "smartstore.naver.com" in u or "shopping.naver.com" in u:
        result = await _parse_naver(html, final_url)
    elif "gmarket.co.kr" in u:
        result = await _parse_gmarket(html, final_url)
    elif "auction.co.kr" in u:
        result = await _parse_gmarket(html, final_url)
    else:
        # 일반 fallback: OG + JSON-LD
        result = ParsedProduct(source="etc")
        ld = _extract_json_ld(html)
        og = _extract_og(html)
        result.title = _clean_title(ld.get("name") or og.get("title") or "")
        result.image_url = og.get("image", "")
        offers = ld.get("offers", {})
        if isinstance(offers, list):
            offers = offers[0]
        if offers.get("price"):
            result.sale_price = _parse_price(str(offers["price"]))

    # 할인율 계산 (미설정 시)
    if result.sale_price and result.original_price and not result.discount_rate:
        if result.original_price > result.sale_price:
            result.discount_rate = round((1 - result.sale_price / result.original_price) * 100, 1)

    # 정가 = 판매가인 경우 (할인 없음) → 정가 None으로
    if result.original_price and result.sale_price and result.original_price <= result.sale_price:
        result.original_price = None
        result.discount_rate = None

    if not result.title:
        result.error = "제목을 파싱할 수 없습니다"

    logger.info(f"[URLParser] {result.source} | {result.title[:40]} | {result.sale_price}원 (정가 {result.original_price}원)")
    return result
