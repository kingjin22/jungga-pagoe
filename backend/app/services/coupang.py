"""
쿠팡 파트너스 API 서비스
Docs: https://developers.coupang.com/
"""
import hmac
import hashlib
import datetime
import httpx
from app.config import settings


COUPANG_API_BASE = "https://api-gateway.coupang.com"


def _generate_hmac_signature(method: str, url: str, secret_key: str) -> tuple[str, str]:
    """쿠팡 API HMAC 서명 생성"""
    datetime_str = datetime.datetime.utcnow().strftime("%y%m%dT%H%M%SZ")
    message = datetime_str + method + url
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    return datetime_str, signature


def get_authorization_header(method: str, url: str) -> dict:
    """쿠팡 API 인증 헤더 생성"""
    datetime_str, signature = _generate_hmac_signature(
        method, url, settings.COUPANG_SECRET_KEY
    )
    return {
        "Authorization": f"CEA algorithm=HmacSHA256, access-key={settings.COUPANG_ACCESS_KEY}, signed-date={datetime_str}, signature={signature}"
    }


async def get_best_deals(category_id: str = None, limit: int = 20) -> list[dict]:
    """
    쿠팡 베스트딜 조회
    실제 API 키가 있으면 live 데이터, 없으면 mock 반환
    """
    if not settings.COUPANG_ACCESS_KEY:
        return _get_mock_coupang_deals()

    url = "/v2/providers/affiliate_open_api/apis/openapi/v1/products/bestcategories/1"
    headers = get_authorization_header("GET", url)
    headers["Content-Type"] = "application/json;charset=UTF-8"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                COUPANG_API_BASE + url,
                headers=headers,
                params={"categoryId": category_id, "limit": limit}
            )
            response.raise_for_status()
            data = response.json()
            return _parse_coupang_response(data)
        except Exception as e:
            print(f"쿠팡 API 오류: {e}")
            return _get_mock_coupang_deals()


async def get_affiliate_link(product_url: str) -> str:
    """일반 쿠팡 링크 → 파트너스 링크 변환"""
    if not settings.COUPANG_ACCESS_KEY:
        return product_url  # API 키 없으면 원본 URL 반환

    url = "/v2/providers/affiliate_open_api/apis/openapi/v1/deeplink"
    payload = {"coupangUrls": [product_url]}
    headers = get_authorization_header("POST", url)
    headers["Content-Type"] = "application/json;charset=UTF-8"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                COUPANG_API_BASE + url,
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
            links = data.get("data", {}).get("landingUrls", [])
            return links[0] if links else product_url
        except Exception as e:
            print(f"파트너스 링크 변환 오류: {e}")
            return product_url


def _parse_coupang_response(data: dict) -> list[dict]:
    """쿠팡 API 응답 파싱"""
    deals = []
    for item in data.get("data", {}).get("productData", []):
        deals.append({
            "title": item.get("productName", ""),
            "original_price": item.get("originalPrice", 0),
            "sale_price": item.get("salePrice", 0),
            "image_url": item.get("productImage", ""),
            "product_url": item.get("productUrl", ""),
            "affiliate_url": item.get("shortUrl", ""),
            "source": "coupang",
        })
    return deals


def _get_mock_coupang_deals() -> list[dict]:
    """API 키 없을 때 개발용 목업 데이터"""
    return [
        {
            "title": "[쿠팡] 삼성 갤럭시 버즈3 프로 무선이어폰",
            "original_price": 299000,
            "sale_price": 179000,
            "image_url": "https://via.placeholder.com/300x300/E31E24/white?text=버즈3+Pro",
            "product_url": "https://www.coupang.com/vp/products/sample1",
            "affiliate_url": "https://link.coupang.com/sample1",
            "source": "coupang",
        },
        {
            "title": "[쿠팡로켓] 다이슨 V12 무선청소기 + 헤파필터",
            "original_price": 899000,
            "sale_price": 599000,
            "image_url": "https://via.placeholder.com/300x300/E31E24/white?text=다이슨+V12",
            "product_url": "https://www.coupang.com/vp/products/sample2",
            "affiliate_url": "https://link.coupang.com/sample2",
            "source": "coupang",
        },
        {
            "title": "[쿠팡] LG 올레드 TV 55인치 4K",
            "original_price": 2200000,
            "sale_price": 1490000,
            "image_url": "https://via.placeholder.com/300x300/E31E24/white?text=LG+OLED",
            "product_url": "https://www.coupang.com/vp/products/sample3",
            "affiliate_url": "https://link.coupang.com/sample3",
            "source": "coupang",
        },
    ]
