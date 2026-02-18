"""
네이버 쇼핑 API 서비스
Docs: https://developers.naver.com/docs/serviceapi/search/shopping/shopping.md
"""
import httpx
from app.config import settings


NAVER_API_BASE = "https://openapi.naver.com/v1"


async def search_deals(keyword: str, display: int = 20, sort: str = "date") -> list[dict]:
    """
    네이버 쇼핑 검색 API
    sort: sim(정확도), date(최신순), asc(가격낮은순), dsc(가격높은순)
    """
    if not settings.NAVER_CLIENT_ID:
        return _get_mock_naver_deals()

    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{NAVER_API_BASE}/search/shop.json",
                headers=headers,
                params={
                    "query": keyword,
                    "display": display,
                    "sort": sort,
                    "filter": "naverpay",  # 네이버페이 가능 상품만
                }
            )
            response.raise_for_status()
            data = response.json()
            return _parse_naver_response(data)
        except Exception as e:
            print(f"네이버 API 오류: {e}")
            return _get_mock_naver_deals()


async def get_hot_deals() -> list[dict]:
    """오늘의 핫딜 키워드로 검색"""
    hot_keywords = ["오늘만특가", "핫딜", "반값특가", "타임딜"]
    all_deals = []

    for keyword in hot_keywords[:2]:  # API 호출 최소화
        deals = await search_deals(keyword, display=10)
        all_deals.extend(deals)

    return all_deals


def _parse_naver_response(data: dict) -> list[dict]:
    """네이버 API 응답 파싱"""
    deals = []
    for item in data.get("items", []):
        original_price = int(item.get("hprice", 0) or item.get("lprice", 0))
        sale_price = int(item.get("lprice", 0))

        if original_price == 0:
            original_price = int(sale_price * 1.3)  # 할인율 30%로 가정

        deals.append({
            "title": item.get("title", "").replace("<b>", "").replace("</b>", ""),
            "original_price": original_price,
            "sale_price": sale_price,
            "image_url": item.get("image", ""),
            "product_url": item.get("link", ""),
            "affiliate_url": None,
            "source": "naver",
        })
    return deals


def _get_mock_naver_deals() -> list[dict]:
    """API 키 없을 때 개발용 목업 데이터"""
    return [
        {
            "title": "[네이버쇼핑] 나이키 에어맥스 270 운동화",
            "original_price": 179000,
            "sale_price": 89900,
            "image_url": "https://via.placeholder.com/300x300/03C75A/white?text=나이키+에어맥스",
            "product_url": "https://shopping.naver.com/product/sample1",
            "affiliate_url": None,
            "source": "naver",
        },
        {
            "title": "[네이버페이특가] 에어팟 프로 2세대 USB-C",
            "original_price": 359000,
            "sale_price": 249000,
            "image_url": "https://via.placeholder.com/300x300/03C75A/white?text=에어팟+프로",
            "product_url": "https://shopping.naver.com/product/sample2",
            "affiliate_url": None,
            "source": "naver",
        },
        {
            "title": "[네이버쇼핑] 구스다운 패딩 80수 헝가리",
            "original_price": 450000,
            "sale_price": 189000,
            "image_url": "https://via.placeholder.com/300x300/03C75A/white?text=구스다운+패딩",
            "product_url": "https://shopping.naver.com/product/sample3",
            "affiliate_url": None,
            "source": "naver",
        },
    ]
