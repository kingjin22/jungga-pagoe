"""
브랜드 딜 수집기
전략: 공식 정가(MSRP) 테이블 × 네이버 쇼핑 현재가 → 진짜 할인율
- Apple/Samsung/Dyson/Nike/Sony 등 정가가 고정된 브랜드 대상
- Naver API lprice (현재 최저가) < MSRP 이면 실제 할인
- "네이버 최저가 기준, 정가 대비 X% 저렴" — 신뢰도 높음
"""
import httpx
import re
import asyncio
import logging
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)
NAVER_API_BASE = "https://openapi.naver.com/v1"

MIN_DISCOUNT_PCT = 10  # 10% 이상 할인만
MAX_DISCOUNT_PCT = 55  # 55% 초과 = 가품/잘못된 매칭 의심 → 제외 (강화)
MIN_PRICE_KRW   = 10_000
MIN_PRICE_RATIO  = 0.30  # 기본: MSRP 30% 미만 제외

# 카테고리별 강화 기준 (가품 위험 높은 카테고리)
CATEGORY_MIN_RATIO = {
    "신발": 0.50,   # 신발 정가 50% 미만 = 가품 의심 (나이키 36%는 제외)
    "패션": 0.45,   # 패션도 45% 이상만
    "뷰티": 0.40,   # 뷰티 40%
}

# ────────────────────────────────────────────────────────────────────────
# 공식 정가(MSRP) 테이블 — 한국 공식 정가 기준
# 출처: 브랜드 공식 사이트, 네이버 쇼핑 정가 표시
# 업데이트 주기: 새 모델 출시 시 수동 추가
# ────────────────────────────────────────────────────────────────────────
PRODUCT_MSRP: list[dict] = [
    # ── Apple ──────────────────────────────────────────────────────────
    {"query": "에어팟 프로 3세대 MagSafe USB-C",  "msrp": 359_000, "category": "전자기기", "brand": "Apple"},
    {"query": "에어팟 4 ANC Apple",               "msrp": 229_000, "category": "전자기기", "brand": "Apple"},
    {"query": "에어팟 맥스 USB-C Apple",           "msrp": 699_000, "category": "전자기기", "brand": "Apple"},
    {"query": "애플워치 시리즈10 GPS 42mm",         "msrp": 559_000, "category": "전자기기", "brand": "Apple"},
    {"query": "아이패드 에어 11인치 M2 2024",       "msrp": 899_000, "category": "전자기기", "brand": "Apple"},
    {"query": "아이패드 미니 7세대 2024",           "msrp": 799_000, "category": "전자기기", "brand": "Apple"},
    # ── Samsung ────────────────────────────────────────────────────────
    {"query": "삼성 갤럭시 버즈3 프로",            "msrp": 329_000, "category": "전자기기", "brand": "Samsung"},
    {"query": "삼성 갤럭시 버즈3",                 "msrp": 199_000, "category": "전자기기", "brand": "Samsung"},
    {"query": "삼성 갤럭시워치7 44mm",             "msrp": 329_000, "category": "전자기기", "brand": "Samsung"},
    {"query": "삼성 갤럭시탭 S9 FE 256GB",        "msrp": 779_000, "category": "전자기기", "brand": "Samsung"},
    # ── Sony ───────────────────────────────────────────────────────────
    {"query": "소니 WH-1000XM5 헤드폰",            "msrp": 449_000, "category": "전자기기", "brand": "Sony"},
    {"query": "소니 WF-1000XM5 이어폰",            "msrp": 369_000, "category": "전자기기", "brand": "Sony"},
    {"query": "소니 WH-1000XM4 헤드폰",            "msrp": 379_000, "category": "전자기기", "brand": "Sony"},
    # ── Bose ───────────────────────────────────────────────────────────
    {"query": "보스 QuietComfort Ultra 헤드폰",    "msrp": 499_000, "category": "전자기기", "brand": "Bose"},
    {"query": "보스 QuietComfort Earbuds 3",       "msrp": 349_000, "category": "전자기기", "brand": "Bose"},
    # ── Dyson ──────────────────────────────────────────────────────────
    {"query": "다이슨 에어랩 컴플리트 롱",          "msrp": 999_000, "category": "생활가전", "brand": "Dyson"},
    {"query": "다이슨 슈퍼소닉 드라이어",           "msrp": 649_000, "category": "생활가전", "brand": "Dyson"},
    {"query": "다이슨 V15 디텍트 청소기",           "msrp": 1_099_000, "category": "생활가전", "brand": "Dyson"},
    {"query": "다이슨 Gen5 Detect 청소기",         "msrp": 1_299_000, "category": "생활가전", "brand": "Dyson"},
    # ── LG ─────────────────────────────────────────────────────────────
    {"query": "LG 그램 16 2024 노트북",            "msrp": 1_979_000, "category": "전자기기", "brand": "LG"},
    {"query": "LG 그램 14 2024 노트북",            "msrp": 1_679_000, "category": "전자기기", "brand": "LG"},
    {"query": "LG 코드제로 A9S 청소기",            "msrp": 849_000, "category": "생활가전", "brand": "LG"},
    # ── 신발 ─────────────────────────────────────────────────────────
    {"query": "나이키 에어포스1 07 운동화",         "msrp": 129_000, "category": "신발", "brand": "Nike"},
    {"query": "나이키 에어맥스 97 운동화",          "msrp": 199_000, "category": "신발", "brand": "Nike"},
    {"query": "나이키 페가수스 41 런닝화",          "msrp": 159_000, "category": "신발", "brand": "Nike"},
    {"query": "아디다스 스탠스미스 스니커즈",        "msrp": 149_000, "category": "신발", "brand": "Adidas"},
    {"query": "아디다스 울트라부스트 22 런닝화",     "msrp": 229_000, "category": "신발", "brand": "Adidas"},
    {"query": "뉴발란스 993 스니커즈",              "msrp": 259_000, "category": "신발", "brand": "New Balance"},
    {"query": "뉴발란스 530 스니커즈",              "msrp": 109_000, "category": "신발", "brand": "New Balance"},
    {"query": "뉴발란스 1906R 스니커즈",            "msrp": 179_000, "category": "신발", "brand": "New Balance"},
    {"query": "호카 클리프톤 9 런닝화",             "msrp": 179_000, "category": "신발", "brand": "Hoka"},
    {"query": "호카 본다이 8 런닝화",               "msrp": 219_000, "category": "신발", "brand": "Hoka"},
    {"query": "아식스 젤카야노 31 런닝화",          "msrp": 209_000, "category": "신발", "brand": "Asics"},
    {"query": "살로몬 스피드크로스6 트레일화",       "msrp": 179_000, "category": "신발", "brand": "Salomon"},
    # ── 패딩/아웃도어 ──────────────────────────────────────────────
    {"query": "노스페이스 눕시 패딩 2024",          "msrp": 359_000, "category": "패션", "brand": "The North Face"},
    {"query": "파타고니아 다운 재킷",               "msrp": 459_000, "category": "패션", "brand": "Patagonia"},
    {"query": "유니클로 울트라라이트 다운 재킷",     "msrp":  69_900, "category": "패션", "brand": "Uniqlo"},
    # ── 뷰티 ─────────────────────────────────────────────────────────
    {"query": "에스티로더 어드밴스드 나이트 리페어 세럼 75ml", "msrp": 159_000, "category": "뷰티", "brand": "Estee Lauder"},
    {"query": "SK-II 페이셜 트리트먼트 에센스 230ml",         "msrp": 310_000, "category": "뷰티", "brand": "SK-II"},
    {"query": "설화수 자음생 크림 75ml",            "msrp": 135_000, "category": "뷰티", "brand": "Sulwhasoo"},
    {"query": "이니스프리 그린티 씨드 세럼 80ml",   "msrp":  39_000, "category": "뷰티", "brand": "Innisfree"},
    # ── 커피/주방 ─────────────────────────────────────────────────
    {"query": "네스프레소 버츄오 팝 커피머신",      "msrp": 219_000, "category": "생활가전", "brand": "Nespresso"},
    {"query": "드롱기 디디카 에스프레소 머신",       "msrp": 399_000, "category": "생활가전", "brand": "De'Longhi"},
    {"query": "쿠쿠 IH 압력밥솥 6인용",            "msrp": 279_000, "category": "생활가전", "brand": "Cuckoo"},
    {"query": "필립스 에어프라이어 XXL",            "msrp": 219_000, "category": "생활가전", "brand": "Philips"},
]


def _clean_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _brand_in_title(brand: str, title: str) -> bool:
    """결과 제목에 브랜드명이 실제로 포함되어 있는지 확인 (가품 필터)"""
    title_lower = title.lower()
    brand_lower = brand.lower()
    # 브랜드명 별칭 매핑
    aliases = {
        "nike": ["나이키", "nike"],
        "adidas": ["아디다스", "adidas"],
        "new balance": ["뉴발란스", "new balance", "newbalance", "NB"],
        "hoka": ["호카", "hoka"],
        "asics": ["아식스", "asics"],
        "salomon": ["살로몬", "salomon"],
        "apple": ["애플", "apple", "에어팟", "아이패드", "airpods", "ipad", "applewatch"],
        "samsung": ["삼성", "samsung", "갤럭시", "galaxy"],
        "sony": ["소니", "sony"],
        "bose": ["보스", "bose"],
        "dyson": ["다이슨", "dyson"],
        "lg": ["lg", "엘지"],
        "the north face": ["노스페이스", "north face", "northface"],
        "patagonia": ["파타고니아", "patagonia"],
        "uniqlo": ["유니클로", "uniqlo"],
        "estee lauder": ["에스티로더", "estee lauder"],
        "sk-ii": ["sk-ii", "sk ii", "skii"],
        "sulwhasoo": ["설화수", "sulwhasoo"],
        "innisfree": ["이니스프리", "innisfree"],
        "nespresso": ["네스프레소", "nespresso"],
        "de'longhi": ["드롱기", "delonghi", "de'longhi"],
        "cuckoo": ["쿠쿠", "cuckoo"],
        "philips": ["필립스", "philips"],
    }
    checks = aliases.get(brand_lower, [brand_lower])
    return any(alias.lower() in title_lower for alias in checks)


async def _get_naver_lprice(query: str, headers: dict, client: httpx.AsyncClient) -> Optional[tuple]:
    """네이버 쇼핑 현재 최저가 + 이미지 + 링크 반환"""
    try:
        resp = await client.get(
            f"{NAVER_API_BASE}/search/shop.json",
            headers=headers,
            params={"query": query, "display": 5, "sort": "sim"},
            timeout=8.0,
        )
        resp.raise_for_status()
        items = resp.json().get("items", [])
    except Exception:
        return None

    if not items:
        return None

    # 최저가 상품 선택
    best = min(items, key=lambda x: int(x.get("lprice", 999_999_999) or 999_999_999))
    lp = int(best.get("lprice", 0) or 0)
    if lp < MIN_PRICE_KRW:
        return None

    return lp, best.get("image", ""), best.get("link", ""), _clean_html(best.get("title", ""))


async def collect_brand_deals(min_discount: float = MIN_DISCOUNT_PCT) -> list[dict]:
    """
    MSRP 테이블 × Naver 현재가 → 실제 할인 딜 목록 반환
    할인율 = (1 - 현재가 / 공식정가) × 100
    """
    if not settings.NAVER_CLIENT_ID:
        return []

    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }

    results = []
    async with httpx.AsyncClient() as client:
        for product in PRODUCT_MSRP:
            await asyncio.sleep(0.08)  # API rate limit
            naver = await _get_naver_lprice(product["query"], headers, client)
            if not naver:
                continue

            lprice, image, link, found_title = naver
            msrp = product["msrp"]

            if lprice >= msrp:
                continue  # 정가 이상이면 딜 아님

            # 1. 카테고리별 최소 가격 비율 (가품 필터)
            cat = product["category"]
            min_ratio = CATEGORY_MIN_RATIO.get(cat, MIN_PRICE_RATIO)
            if lprice < msrp * min_ratio:
                logger.debug(f"  ✗ {product['brand']} — 가격 비합리 ({lprice:,}원 < MSRP×{min_ratio:.0%})")
                continue

            # 2. 결과 제목에 브랜드명 포함 여부 (가품/잘못된 매칭 필터)
            if not _brand_in_title(product["brand"], found_title):
                logger.debug(f"  ✗ {product['brand']} — 브랜드명 미포함: '{found_title[:40]}'")
                continue

            discount_rate = round((1 - lprice / msrp) * 100, 1)
            if discount_rate < min_discount or discount_rate > MAX_DISCOUNT_PCT:
                continue
            if not link:
                continue

            # 제목: 브랜드 + 검색어에서 모델명 추출
            title_parts = product["query"].split()
            title = " ".join(title_parts[:5])  # 앞 5단어

            results.append({
                "title": f"[{product['brand']}] {title}",
                "original_price": float(msrp),
                "sale_price": float(lprice),
                "discount_rate": discount_rate,
                "image_url": image if image.startswith("http") else None,
                "product_url": link,
                "source": "naver",
                "category": product["category"],
                "is_hot": discount_rate >= 20,
                "description": f"공식 정가 {msrp:,}원 대비 {discount_rate:.0f}% 저렴한 현재 최저가",
            })
            logger.debug(f"  ✓ {product['brand']} {title[:30]} | -{discount_rate:.0f}% ({lprice:,}원 / 정가 {msrp:,}원)")

    results.sort(key=lambda x: x["discount_rate"], reverse=True)
    print(f"[브랜드딜] {len(results)}개 (min {min_discount}%)", flush=True)
    return results
