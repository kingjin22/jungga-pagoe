"""
뽐뿌 RSS 파서 - 한국 최대 핫딜 커뮤니티
RSS URL: https://www.ppomppu.co.kr/rss.php?id=ppomppu
실제 사용자들이 검증한 진행 중인 딜만 올라오는 구조
"""
import httpx
import re
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Optional


RSS_URLS = {
    "ppomppu": "https://www.ppomppu.co.kr/rss.php?id=ppomppu",       # 뽐뿌 게시판 (쇼핑 핫딜)
    "ppomppu_foreign": "https://www.ppomppu.co.kr/rss.php?id=ppomppu4",  # 해외 핫딜
}

# 제목에서 가격 추출 정규식
PRICE_PATTERNS = [
    r'[\(（]([0-9,]+)원[\)）]',           # (12,000원)
    r'[\(（]([0-9,]+)원?\s*/\s*무료[\)）]', # (12,000원/무료)
    r'([0-9,]+)원',                         # 12,000원
    r'₩([0-9,]+)',                           # ₩12,000
    r'\$([0-9.]+)',                           # $12.99
]

# 카테고리 추론은 services/categorizer.py 참조


def _clean_title(title: str) -> str:
    """제목 정제"""
    # [광고], (끌올) 등 태그 제거
    title = re.sub(r'^\s*[\(（\[【]?(끌올|광고|삭제|완료|종료|마감)\s*[\)）\]】]?\s*', '', title, flags=re.IGNORECASE)
    title = title.strip()
    return title


def _extract_price_from_title(title: str) -> Optional[int]:
    """제목에서 가격 추출"""
    for pattern in PRICE_PATTERNS:
        match = re.search(pattern, title)
        if match:
            price_str = match.group(1).replace(",", "").replace(".", "")
            try:
                price = int(float(price_str))
                if 100 <= price <= 100_000_000:  # 100원 ~ 1억 사이
                    return price
            except:
                continue
    return None


def _extract_discount_from_title(title: str) -> Optional[float]:
    """제목에서 할인율 추출"""
    patterns = [
        r'(\d{1,2})%\s*할인',
        r'(\d{1,2})%\s*off',
        r'(\d{1,2})프로\s*할인',
        r'반값',
        r'50%',
    ]
    for pattern in patterns:
        if "반값" in pattern and "반값" in title:
            return 50.0
        match = re.search(pattern, title, re.IGNORECASE)
        if match and match.lastindex:
            rate = float(match.group(1))
            if 5 <= rate <= 95:
                return rate
    return None


def _guess_category(title: str) -> str:
    from app.services.categorizer import infer_category
    return infer_category(title)


def _is_valid_deal(title: str) -> bool:
    """유효한 딜인지 필터링 (광고, 완료된 딜 제외)"""
    invalid_keywords = ["완료", "종료", "마감", "삭제", "광고", "공지", "안내"]
    for kw in invalid_keywords:
        if kw in title:
            return False
    return True


def _parse_rss_item(item) -> Optional[dict]:
    """RSS 아이템 하나를 딜 dict로 변환"""
    title_tag = item.find("title")
    link_tag = item.find("link")
    desc_tag = item.find("description")

    if not title_tag or not link_tag:
        return None

    raw_title = title_tag.get_text(strip=True)
    title = _clean_title(raw_title)
    link = link_tag.get_text(strip=True) if link_tag.string else str(link_tag.next_sibling).strip()

    if not title or not link:
        return None

    if not _is_valid_deal(title):
        return None

    # link 태그 처리 (RSS에서 CDATA 방식으로 올 수 있음)
    if not link.startswith("http"):
        return None

    description = ""
    if desc_tag:
        desc_text = desc_tag.get_text(strip=True)
        description = desc_text[:200] if desc_text else ""

    # 가격 추출
    sale_price = _extract_price_from_title(title)
    discount_rate = _extract_discount_from_title(title)
    category = _guess_category(title)

    # 가격 정보가 없으면 스킵 (신뢰성 없는 데이터)
    if not sale_price:
        return None

    # 할인율 기반 원가 역산 or 기본값
    if discount_rate and discount_rate > 0:
        original_price = round(sale_price / (1 - discount_rate / 100))
    else:
        # 할인율 모르면 최소 10% 가정 (보수적)
        original_price = round(sale_price / 0.85)
        discount_rate = 15.0

    return {
        "title": title,
        "description": description,
        "original_price": float(original_price),
        "sale_price": float(sale_price),
        "discount_rate": discount_rate,
        "image_url": None,
        "product_url": link,
        "affiliate_url": None,
        "source": "community",
        "category": category,
    }


async def fetch_ppomppu_deals() -> list[dict]:
    """
    뽐뿌 RSS 수집 → 각 포스트에서 실제 상품 URL + 이미지 추출
    """
    from app.services.image_fetcher import enrich_deal_with_image
    import asyncio

    raw_deals = []
    seen_ppomppu_urls = set()

    async with httpx.AsyncClient() as client:
        for name, url in RSS_URLS.items():
            try:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; JunggaPagoeBot/1.0)"},
                    timeout=15.0,
                    follow_redirects=True,
                )
                resp.raise_for_status()

                soup = BeautifulSoup(resp.text, "xml")
                items = soup.find_all("item")
                print(f"  [뽐뿌/{name}] {len(items)}개 RSS 파싱 중...")

                for item in items:
                    deal = _parse_rss_item(item)
                    if deal and deal["product_url"] not in seen_ppomppu_urls:
                        seen_ppomppu_urls.add(deal["product_url"])
                        raw_deals.append(deal)

            except Exception as e:
                print(f"  [뽐뿌/{name}] RSS 오류: {e}")

    print(f"  [뽐뿌] RSS 파싱: {len(raw_deals)}개 → 이미지/상품URL 추출 시작...")

    # 각 포스트에서 실제 상품 URL + 이미지 병렬 추출 (최대 5개씩 배치)
    enriched = []
    seen_product_urls = set()

    for i in range(0, len(raw_deals), 5):
        batch = raw_deals[i:i+5]
        tasks = [enrich_deal_with_image(deal) for deal in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for deal in results:
            if isinstance(deal, Exception):
                continue
            url = deal.get("product_url", "")
            if url and url not in seen_product_urls:
                seen_product_urls.add(url)
                enriched.append(deal)

        # 서버 부하 방지
        await asyncio.sleep(0.5)

    print(f"[뽐뿌] 완료: {len(enriched)}개 (이미지 포함)")
    return enriched
