"""
뽐뿌 RSS 파서
역할: RSS에서 제목과 가격만 추출
이미지/상품URL은 네이버 쇼핑 API에서 가져옴 (스크래핑 없음)
"""
import httpx
import re
import asyncio
import html
from bs4 import BeautifulSoup
from typing import Optional

RSS_URLS = {
    "ppomppu": "https://www.ppomppu.co.kr/rss.php?id=ppomppu",
    "ppomppu_foreign": "https://www.ppomppu.co.kr/rss.php?id=ppomppu4",
}

KRW_PRICE_PATTERNS = [
    r'[\(（]([0-9,]+)원[^\)）]{0,10}[\)）]',
    r'([0-9,]+)원',
    r'₩([0-9,]+)',
]

INVALID_KEYWORDS = ["완료", "종료", "마감", "삭제", "광고", "공지"]


def _clean_title(title: str) -> str:
    title = re.sub(r'^\s*[\(（\[【]?\s*(끌올|광고|삭제|완료|종료|마감)\s*[\)）\]】]?\s*', '', title, flags=re.IGNORECASE)
    return title.strip()


def _extract_krw_price(title: str) -> Optional[int]:
    for pattern in KRW_PRICE_PATTERNS:
        m = re.search(pattern, title)
        if m:
            try:
                price = int(m.group(1).replace(",", ""))
                if 500 <= price <= 50_000_000:
                    return price
            except Exception:
                continue
    return None


def _extract_discount_rate(title: str) -> Optional[float]:
    m = re.search(r'(\d{1,2})\s*%\s*(할인|off|세일)', title, re.IGNORECASE)
    if m:
        rate = float(m.group(1))
        if 5 <= rate <= 95:
            return rate
    if "반값" in title:
        return 50.0
    return None


def _parse_item(item) -> Optional[dict]:
    title_tag = item.find("title")
    link_tag = item.find("link")
    desc_tag = item.find("description")

    if not title_tag or not link_tag:
        return None

    raw_title = title_tag.get_text(strip=True)
    title = _clean_title(raw_title)
    if not title or any(kw in title for kw in INVALID_KEYWORDS):
        return None

    link = link_tag.get_text(strip=True) if link_tag.string else str(link_tag.next_sibling or "").strip()
    if not link.startswith("http"):
        return None

    sale_price = _extract_krw_price(title)
    if not sale_price:
        return None  # 원화 가격 없는 딜 제외 (달러 해외딜 등)

    discount_rate = _extract_discount_rate(title)
    original_price = round(sale_price / (1 - discount_rate / 100)) if discount_rate else sale_price

    description = ""
    if desc_tag:
        raw = desc_tag.get_text(separator=" ", strip=True)
        raw = html.unescape(raw)
        raw = re.sub(r'[\s\xa0]+', ' ', raw).strip()
        description = raw[:200]

    from app.services.categorizer import infer_category
    return {
        "title": title,
        "description": description or None,
        "sale_price": float(sale_price),
        "original_price": float(original_price),
        "discount_rate": discount_rate or 0.0,
        "ppomppu_url": link,  # 뽐뿌 원본 링크 (fallback용)
        "category": infer_category(title),
    }


async def fetch_ppomppu_deals() -> list[dict]:
    """
    뽐뿌 RSS → 제목/가격 파싱 → 네이버 쇼핑으로 이미지/URL enrichment
    """
    from app.services.naver import search_product

    raw = []
    seen = set()

    async with httpx.AsyncClient() as client:
        for name, url in RSS_URLS.items():
            try:
                resp = await client.get(
                    url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=15.0,
                    follow_redirects=True,
                )
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "xml")
                for item in soup.find_all("item"):
                    d = _parse_item(item)
                    if d and d["ppomppu_url"] not in seen:
                        seen.add(d["ppomppu_url"])
                        raw.append(d)
                print(f"  [뽐뿌/{name}] {len([i for i in soup.find_all('item')])}개 중 {len(raw)}개 가격 있음")
            except Exception as e:
                print(f"  [뽐뿌/{name}] 오류: {e}")

    print(f"  네이버 쇼핑으로 이미지/URL enrichment 시작 ({len(raw)}개)...")

    # 네이버 쇼핑 API로 enrichment (5개씩 병렬)
    enriched = []
    for i in range(0, len(raw), 5):
        batch = raw[i:i+5]
        tasks = [search_product(d["title"]) for d in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for deal, nav in zip(batch, results):
            if isinstance(nav, Exception):
                nav = {}
            # 가격은 뽐뿌 제목 기준 (신뢰)
            # 할인율은 제목에 명시된 경우만 (없으면 0 → 뱃지 미표시)
            # 이미지/URL만 네이버에서 사용
            ppomppu_price = deal["sale_price"]
            dr = deal["discount_rate"]
            orig = deal["original_price"]

            enriched.append({
                "title": deal["title"],
                "description": deal["description"],
                "sale_price": ppomppu_price,
                "original_price": orig,
                "discount_rate": dr,
                "image_url": nav.get("image_url"),
                "product_url": nav.get("product_url") or deal["ppomppu_url"],
                "category": nav.get("naver_category") or deal["category"],
                "source": "community",
                "submitter_name": "뽐뿌",
            })
        await asyncio.sleep(0.2)

    ok_img = sum(1 for d in enriched if d.get("image_url"))
    ok_url = sum(1 for d in enriched if "ppomppu" not in d.get("product_url", ""))
    print(f"[뽐뿌] 완료: {len(enriched)}개 | 이미지: {ok_img}개 | 쇼핑몰URL: {ok_url}개")
    return enriched
