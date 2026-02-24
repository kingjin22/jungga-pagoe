"""
네이버 쇼핑 API 서비스
핵심 원칙: hprice(정가) > lprice(최저가) 인 상품만 수집 → 네이버가 직접 검증한 진짜 할인
"""
import httpx
import re
from app.config import settings

NAVER_API_BASE = "https://openapi.naver.com/v1"

# 카테고리별 검색 키워드 (실제 상품명 위주 → 정가 비교 데이터 풍부)
CATEGORY_KEYWORDS = {
    "전자기기": [
        "무선이어폰", "블루투스이어폰", "무선청소기", "공기청정기",
        "로봇청소기", "스마트워치", "태블릿PC", "노트북",
        "게이밍마우스", "게이밍키보드", "블루투스스피커", "보조배터리",
        "캠코더", "미러리스카메라", "액션캠"
    ],
    "패션": [
        "구스다운패딩", "롱패딩", "스니커즈", "나이키운동화",
        "아디다스운동화", "뉴발란스운동화", "겨울코트", "기능성재킷",
        "플리스자켓", "바람막이", "레인코트"
    ],
    "뷰티": [
        "선크림", "에센스", "세럼", "클렌징폼",
        "수분크림", "토너패드", "선스틱", "콜라겐앰플"
    ],
    "생활가전": [
        "에어프라이어", "전기압력밥솥", "커피머신",
        "전기면도기", "헤어드라이기", "식기세척기",
        "전자레인지", "공기청정기", "제습기"
    ],
    "스포츠": [
        "러닝화", "등산화", "사이클링헬멧",
        "요가매트", "폼롤러", "줄넘기", "배드민턴라켓"
    ],
    "신발": [
        "나이키조던", "아디다스삼바", "뉴발란스530",
        "살로몬트레일화", "호카클리프턴", "아식스겔카야노"
    ],
}

MIN_DISCOUNT_RATE = 10   # 10% 이상만 수집
MIN_PRICE = 3000         # 3천원 이상 상품만


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _map_category(naver_category: str) -> str:
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


async def search_with_real_discount(keyword: str, display: int = 20) -> list[dict]:
    """
    네이버 쇼핑 검색 — hprice 우선, 없으면 lprice 중앙값 비교로 할인 감지
    """
    if not settings.NAVER_CLIENT_ID:
        return []

    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{NAVER_API_BASE}/search/shop.json",
                headers=headers,
                params={
                    "query": keyword,
                    "display": display,
                    "sort": "sim",   # 정확도순
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
        except Exception as e:
            print(f"네이버 API 오류 [{keyword}]: {e}")
            return []

    # 중앙값 계산용: 전체 결과의 lprice 목록
    all_lprices = [
        int(i.get("lprice", 0) or 0)
        for i in items
        if int(i.get("lprice", 0) or 0) >= MIN_PRICE
    ]
    if len(all_lprices) >= 3:
        sorted_all = sorted(all_lprices)
        median_price = sorted_all[len(sorted_all) // 2]
    else:
        median_price = 0

    deals = []
    for item in items:
        title = _strip_html(item.get("title", ""))
        lprice = int(item.get("lprice", 0) or 0)   # 현재 최저가
        hprice = int(item.get("hprice", 0) or 0)   # 최고가/정가

        if lprice <= 0 or lprice < MIN_PRICE:
            continue

        ref_price = 0

        # hprice 우선, 없으면 검색 결과 중앙값으로 대체
        if hprice > 0 and hprice > lprice:
            ref_price = hprice
            discount_rate = round((1 - lprice / hprice) * 100, 1)
            if discount_rate < MIN_DISCOUNT_RATE:
                continue
        else:
            # 같은 검색 결과에서 lprice들의 중앙값 계산
            if median_price > 0 and median_price > lprice * 1.12:  # 중앙값보다 12% 이상 저렴
                ref_price = median_price
                discount_rate = round((1 - lprice / median_price) * 100, 1)
            else:
                continue  # 유의미한 할인 아님 or 비교 데이터 부족

        # ★ 카탈로그 URL 우선: productType=1이면 네이버 최저가 비교 페이지로 연결
        # → 사용자가 클릭하면 항상 현재 최저가가 표시됨 (가격 불일치 방지)
        product_id = item.get("productId", "")
        product_type = str(item.get("productType", "2"))
        if product_type == "1" and product_id:
            product_url = f"https://search.shopping.naver.com/catalog/{product_id}"
        else:
            product_url = item.get("link", "")

        deals.append({
            "title": title,
            "original_price": float(ref_price),
            "sale_price": float(lprice),
            "discount_rate": discount_rate,
            "image_url": item.get("image", ""),
            "product_url": product_url,
            "naver_product_id": product_id,
            "affiliate_url": None,
            "source": "naver",
            "category": _map_category(item.get("category1", "")),
        })

    return deals


async def collect_real_deals(limit_per_keyword: int = 10) -> list[dict]:
    """
    전 카테고리 키워드 순회하며 실제 할인 상품 수집
    중복 URL 제거 후 반환
    """
    all_deals = []
    seen_urls = set()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            deals = await search_with_real_discount(keyword, display=limit_per_keyword)
            for deal in deals:
                if deal["product_url"] and deal["product_url"] not in seen_urls:
                    seen_urls.add(deal["product_url"])
                    all_deals.append(deal)

    # 할인율 높은 순으로 정렬
    all_deals.sort(key=lambda x: x["discount_rate"], reverse=True)
    print(f"[네이버] 실제 할인 상품 수집 완료: {len(all_deals)}개")
    return all_deals


async def get_hot_deals() -> list[dict]:
    """스케줄러용 — collect_real_deals 호출"""
    return await collect_real_deals(limit_per_keyword=5)


def _clean_search_title(title: str) -> str:
    """뽐뿌 제목에서 검색어 추출 — 쇼핑몰 태그/가격/배송 제거"""
    import re
    # [G마켓], [옥션] 등 앞 태그 제거
    title = re.sub(r"^\s*[\[\(【]?[^\]）】]{1,15}[\]\)】]\s*", "", title)
    # (24,440원/무료), (14,900원) 등 가격 제거
    title = re.sub(r"[\(\（][0-9,]+원[^\)）]*[\)\）]", "", title)
    # /무료, /유료 제거
    title = re.sub(r"/\s*(무료|유료|직배)", "", title)
    # 특수문자 정리
    title = re.sub(r"[^\w\s가-힣a-zA-Z0-9]", " ", title)
    return title.strip()[:50]


async def search_product(title: str) -> dict:
    """
    뽐뿌 딜 제목으로 네이버 쇼핑 검색
    → 이미지/가격/URL 반환 (없으면 빈 dict)
    """
    if not settings.NAVER_CLIENT_ID:
        return {}

    query = _clean_search_title(title)
    if not query:
        return {}

    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(
                f"{NAVER_API_BASE}/search/shop.json",
                headers=headers,
                params={"query": query, "display": 3, "sort": "sim"},
                timeout=8.0,
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
        except Exception:
            return {}

    if not items:
        return {}

    # 첫 번째 결과 사용
    item = items[0]
    lprice = int(item.get("lprice", 0) or 0)
    hprice = int(item.get("hprice", 0) or 0)
    image = item.get("image", "")
    link = item.get("link", "")

    return {
        "image_url": image if image.startswith("http") else None,
        "product_url": link if link.startswith("http") else None,
        "naver_lprice": float(lprice) if lprice > 0 else None,
        "naver_hprice": float(hprice) if hprice > 0 else None,
        "naver_category": _map_category(item.get("category1", "")),
    }
