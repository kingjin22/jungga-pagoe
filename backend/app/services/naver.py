"""
네이버 쇼핑 API 서비스
Docs: https://developers.naver.com/docs/serviceapi/search/shopping/shopping.md
"""
import httpx
import re
from app.config import settings


NAVER_API_BASE = "https://openapi.naver.com/v1"

# 핫딜 수집용 키워드 (할인율 높은 상품이 많이 검색되는 키워드)
HOT_DEAL_KEYWORDS = [
    "반값세일",
    "타임딜 특가",
    "오늘만특가",
    "최저가 핫딜",
    "쿠폰할인 특가",
    "브랜드위크 세일",
    "단하루특가",
    "데일리특가",
]


def _strip_html(text: str) -> str:
    """HTML 태그 제거"""
    return re.sub(r"<[^>]+>", "", text).strip()


async def search_deals(keyword: str, display: int = 20, sort: str = "sim") -> list[dict]:
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
                },
                timeout=10.0,
            )
            response.raise_for_status()
            data = response.json()
            return _parse_naver_response(data)
        except Exception as e:
            print(f"네이버 API 오류 [{keyword}]: {e}")
            return []


async def get_hot_deals() -> list[dict]:
    """핫딜 키워드로 다양하게 검색해서 수집"""
    all_deals = []
    seen_urls = set()

    for keyword in HOT_DEAL_KEYWORDS[:4]:  # API 호출 최소화
        deals = await search_deals(keyword, display=10, sort="sim")
        for deal in deals:
            if deal["product_url"] not in seen_urls and deal["discount_rate"] >= 10:
                seen_urls.add(deal["product_url"])
                all_deals.append(deal)

    return all_deals


def _parse_naver_response(data: dict) -> list[dict]:
    """네이버 API 응답 파싱 - 할인율 계산 포함"""
    deals = []
    for item in data.get("items", []):
        title = _strip_html(item.get("title", ""))
        lprice = int(item.get("lprice", 0) or 0)  # 최저가
        hprice = int(item.get("hprice", 0) or 0)  # 상한가 (원가로 활용)
        image = item.get("image", "")
        link = item.get("link", "")
        category = item.get("category1", "")

        if lprice == 0:
            continue  # 가격 없으면 스킵

        # 원가 계산
        # hprice가 있고 lprice보다 높으면 원가로 사용
        if hprice > lprice:
            original_price = hprice
        else:
            # hprice 없으면 title에서 할인율 패턴 추출 시도
            discount_in_title = _extract_discount_from_title(title)
            if discount_in_title and discount_in_title >= 10:
                original_price = round(lprice / (1 - discount_in_title / 100))
            else:
                # 최저가만 있으면 스킵 (할인율 계산 불가)
                continue

        discount_rate = round((1 - lprice / original_price) * 100, 1)

        # 10% 미만 할인은 딜로 보기 어려움
        if discount_rate < 10:
            continue

        deals.append({
            "title": title,
            "original_price": original_price,
            "sale_price": lprice,
            "discount_rate": discount_rate,
            "image_url": image,
            "product_url": link,
            "affiliate_url": None,
            "source": "naver",
            "category": _map_category(category),
        })

    return deals


def _extract_discount_from_title(title: str):
    """상품명에서 할인율 추출 (예: '50% 할인', '반값', '30프로')"""
    # "XX% 할인" 패턴
    match = re.search(r"(\d{2,3})\s*%", title)
    if match:
        rate = int(match.group(1))
        if 10 <= rate <= 90:
            return rate

    # "반값" = 50%
    if "반값" in title:
        return 50

    # "XX프로" 패턴
    match = re.search(r"(\d{2,3})\s*프로", title)
    if match:
        rate = int(match.group(1))
        if 10 <= rate <= 90:
            return rate

    return None


def _map_category(naver_category: str) -> str:
    """네이버 카테고리 → 정가파괴 카테고리 매핑"""
    mapping = {
        "패션의류": "패션",
        "패션잡화": "패션",
        "화장품/미용": "뷰티",
        "디지털/가전": "전자기기",
        "가구/인테리어": "홈리빙",
        "식품": "식품",
        "스포츠/레저": "스포츠",
        "출산/육아": "유아동",
    }
    for k, v in mapping.items():
        if k in naver_category:
            return v
    return "기타"


def _get_mock_naver_deals() -> list[dict]:
    """API 키 없을 때 개발용 목업 데이터"""
    return [
        {
            "title": "[네이버쇼핑] 나이키 에어맥스 270 운동화",
            "original_price": 179000,
            "sale_price": 89900,
            "discount_rate": 49.8,
            "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=300",
            "product_url": "https://shopping.naver.com/product/sample1",
            "affiliate_url": None,
            "source": "naver",
            "category": "스포츠",
        },
        {
            "title": "[네이버페이특가] 에어팟 프로 2세대 USB-C",
            "original_price": 359000,
            "sale_price": 249000,
            "discount_rate": 30.6,
            "image_url": "https://images.unsplash.com/photo-1603351154351-5e2d0600bb77?w=300",
            "product_url": "https://shopping.naver.com/product/sample2",
            "affiliate_url": None,
            "source": "naver",
            "category": "전자기기",
        },
    ]
