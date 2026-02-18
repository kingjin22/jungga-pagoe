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
# 원화 가격만 추출 (달러는 환율 불명확 → 제외)
KRW_PRICE_PATTERNS = [
    r'[\(（]([0-9,]+)원[\)）]',            # (12,000원)
    r'[\(（]([0-9,]+)원?\s*/\s*무료[\)）]',  # (12,000원/무료)
    r'([0-9,]+)원',                          # 12,000원
    r'₩([0-9,]+)',                            # ₩12,000
]

# 카테고리 추론은 services/categorizer.py 참조


def _clean_title(title: str) -> str:
    """제목 정제"""
    # [광고], (끌올) 등 태그 제거
    title = re.sub(r'^\s*[\(（\[【]?(끌올|광고|삭제|완료|종료|마감)\s*[\)）\]】]?\s*', '', title, flags=re.IGNORECASE)
    title = title.strip()
    return title


def _extract_price_from_title(title: str) -> Optional[int]:
    """제목에서 원화 가격만 추출 (달러 제외)"""
    for pattern in KRW_PRICE_PATTERNS:
        match = re.search(pattern, title)
        if match:
            price_str = match.group(1).replace(",", "")
            try:
                price = int(price_str)
                if 500 <= price <= 50_000_000:  # 500원 ~ 5천만원
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
        import html
        desc_text = desc_tag.get_text(separator=' ', strip=True)
        # HTML 엔티티 제거 + 연속 공백/개행 정리
        desc_text = html.unescape(desc_text)
        desc_text = re.sub(r'[\s\xa0]+', ' ', desc_text).strip()
        description = desc_text[:200] if desc_text else ""

    # 가격 추출
    sale_price = _extract_price_from_title(title)
    discount_rate = _extract_discount_from_title(title)
    category = _guess_category(title)

    # 가격 정보가 없으면 스킵 (신뢰성 없는 데이터)
    if not sale_price:
        return None

    # 할인율 있을 때만 원가 역산, 없으면 원가=판매가 (가짜 데이터 금지)
    if discount_rate and discount_rate > 0:
        original_price = round(sale_price / (1 - discount_rate / 100))
    else:
        original_price = sale_price
        discount_rate = 0.0

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

    print(f"  [뽐뿌] RSS 파싱: {len(raw_deals)}개 → 상품URL + 이미지 추출 시작...")

    from app.services.image_downloader import download_image

    enriched = []
    seen_product_urls = set()

    for i in range(0, len(raw_deals), 5):
        batch = raw_deals[i:i+5]

        # 1단계: 상품 URL + CDN 이미지 URL 추출
        tasks = [enrich_deal_with_image(deal) for deal in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 2단계: CDN 이미지 로컬 다운로드 (Referer 문제 해결)
        dl_tasks = []
        valid = []
        for deal in results:
            if isinstance(deal, Exception):
                continue
            url = deal.get("product_url", "")
            if url and url not in seen_product_urls:
                seen_product_urls.add(url)
                valid.append(deal)
                dl_tasks.append(download_image(deal.get("image_url") or ""))

        dl_results = await asyncio.gather(*dl_tasks, return_exceptions=True)
        for deal, local_path in zip(valid, dl_results):
            if not isinstance(local_path, Exception) and local_path:
                deal["image_url"] = local_path
            enriched.append(deal)

        await asyncio.sleep(0.3)

    ok_img = sum(1 for d in enriched if d.get("image_url", "").startswith("/images/"))
    ok_url = sum(1 for d in enriched if "ppomppu" not in d.get("product_url", ""))
    print(f"[뽐뿌] 완료: {len(enriched)}개 | 로컬이미지: {ok_img}개 | 쇼핑몰URL: {ok_url}개")
    return enriched
