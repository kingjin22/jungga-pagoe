"""
정가거부 카페 쇼핑 핫딜 게시판 크롤러
- 로그인 없이 공개 API로 제목 수집
- 제목 파싱 → Naver Shopping API 검색 → 가격 검증
"""
import re
import asyncio
import httpx
import logging

logger = logging.getLogger(__name__)

CAFE_ID = 30786704
MENU_ID = 21
CAFE_URL = "wjdrkrjqn"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": f"https://cafe.naver.com/{CAFE_URL}",
}

# 해외 소스 키워드 (제외 대상)
OVERSEAS_KEYWORDS = ["알리", "aliexpress", "amazon", "ebay", "아마존", "타오바오", "stacksocial"]

# 가격 파싱 패턴: "12,345원", "12345원", "1만원", "3500원 무배"
PRICE_PATTERN = re.compile(r'(\d{1,3}(?:,\d{3})*|\d+)\s*원')
PRICE_WAN_PATTERN = re.compile(r'(\d+(?:\.\d+)?)\s*만\s*원')

# 소스 태그 파싱: [쿠팡], [11번가] 등
SOURCE_PATTERN = re.compile(r'^\[?([^\]]{2,10})\]?\s*')


def parse_price_from_title(title: str) -> int | None:
    """제목에서 가격 추출"""
    # 만원 단위
    m = PRICE_WAN_PATTERN.search(title)
    if m:
        return int(float(m.group(1)) * 10000)
    # 원 단위
    m = PRICE_PATTERN.search(title)
    if m:
        return int(m.group(1).replace(",", ""))
    return None


def parse_source_from_title(title: str) -> str:
    """제목 앞 [소스명] 추출"""
    m = SOURCE_PATTERN.match(title)
    if m:
        s = m.group(1).strip("[] ")
        return s if len(s) <= 8 else ""
    return ""


def clean_search_query(title: str) -> str:
    """제목에서 검색어 추출 (가격/무배/특수문자 제거)"""
    # 앞 [소스] 제거
    title = re.sub(r'^\[?[^\]]{2,10}\]?\s*', '', title)
    # 괄호 내용 제거
    title = re.sub(r'\([^)]*\)', '', title)
    title = re.sub(r'\[[^\]]*\]', '', title)
    # 가격/수량 표현 제거
    title = re.sub(r'\d{1,3}(?:,\d{3})*원|\d+원', '', title)
    title = re.sub(r'\d+\s*만\s*원', '', title)
    title = re.sub(r'\d+개|\d+매|\d+팩|\d+l|\d+ml|\d+g|\d+kg', '', title, flags=re.IGNORECASE)
    title = re.sub(r'무(료)?배송?|무배|배송비\s*포함|체험딜|핫딜|특가|할인|세일', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title[:50]


async def fetch_cafe_articles(page: int = 1, per_page: int = 20) -> list[dict]:
    """카페 게시글 목록 수집"""
    url = (
        f"https://apis.naver.com/cafe-web/cafe2/ArticleListV2.json"
        f"?search.clubid={CAFE_ID}&search.menuid={MENU_ID}"
        f"&search.page={page}&search.perPage={per_page}"
    )
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        return data["message"]["result"]["articleList"]


async def fetch_naver_shopping(query: str, client: httpx.AsyncClient) -> dict | None:
    """Naver Shopping API로 제품 검색"""
    from app.config import settings
    try:
        r = await client.get(
            "https://openapi.naver.com/v1/search/shop.json",
            params={"query": query, "display": 3, "sort": "sim"},
            headers={
                "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
                "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
            },
            timeout=5,
        )
        if r.status_code != 200:
            return None
        items = r.json().get("items", [])
        if not items:
            return None
        # 첫 번째 결과 반환
        item = items[0]
        return {
            "naver_title": re.sub('<[^>]+>', '', item.get("title", "")),
            "image_url": item.get("image"),
            "product_url": item.get("link"),
            "lprice": int(item.get("lprice", 0)),
            "hprice": int(item.get("hprice") or 0),
        }
    except Exception as e:
        logger.debug(f"Naver shopping search error: {e}")
        return None


async def fetch_naver_cafe_deals() -> list[dict]:
    """카페 핫딜 → Naver Shopping 매칭 → 딜 목록 반환"""
    from app.services.categorizer import normalize_category

    try:
        articles = await fetch_cafe_articles(page=1, per_page=30)
    except Exception as e:
        logger.error(f"카페 게시글 수집 실패: {e}")
        return []

    deals = []
    async with httpx.AsyncClient(timeout=8) as client:
        for art in articles:
            title: str = re.sub('<[^>]+>', '', art.get("subject", "")).strip()
            if not title:
                continue

            # 해외 소스 제외
            title_lower = title.lower()
            if any(kw in title_lower for kw in OVERSEAS_KEYWORDS):
                continue

            # 제목에서 가격 추출
            sale_price = parse_price_from_title(title)

            # 검색어 정제
            query = clean_search_query(title)
            if len(query) < 4:
                continue

            # Naver Shopping 검색
            naver = await fetch_naver_shopping(query, client)
            if not naver:
                continue

            lprice = naver["lprice"]
            if lprice <= 0:
                continue

            # 커뮤니티 제시 가격 vs 네이버 최저가 비교
            if sale_price and sale_price > 0:
                # 가품 방지: 커뮤니티 가격이 네이버 최저가의 15% 미만이면 스킵
                if sale_price < lprice * 0.15:
                    continue
                # 할인율 계산 (네이버 lprice 기준)
                if sale_price < lprice:
                    discount_rate = round((1 - sale_price / lprice) * 100, 1)
                    original_price = lprice
                    final_sale = sale_price
                else:
                    # 커뮤니티 가격이 네이버보다 비쌈 → 스킵
                    continue
            else:
                # 가격 정보 없으면 스킵
                continue

            # 최소 할인율 10%
            if discount_rate < 10:
                continue

            # 카페 원문 링크
            article_url = f"https://cafe.naver.com/f-e/cafes/{CAFE_ID}/articles/{art.get('articleId')}"

            source_tag = parse_source_from_title(title)
            category = normalize_category(title + " " + query)

            deals.append({
                "title": title[:200],
                "description": f"정가거부 카페 핫딜 | 네이버 최저가 {lprice:,}원 대비 {discount_rate}% 할인",
                "original_price": original_price,
                "sale_price": final_sale,
                "discount_rate": discount_rate,
                "image_url": naver.get("image_url"),
                "product_url": article_url,   # 카페 원문 링크
                "source": "community",
                "category": category,
                "is_hot": discount_rate >= 20,
                "submitter_name": source_tag or "정가거부",
            })
            await asyncio.sleep(0.1)  # API 레이트 리밋 방지

    logger.info(f"✅ 정가거부 카페: {len(deals)}개 딜 수집 (총 {len(articles)}개 중)")
    return deals
