"""
루리웹 핫딜/예판 RSS 파서
- 게시판: https://bbs.ruliweb.com/market/board/1020/rss
- 제목 형식: [판매처] 상품명 (가격/배송)
- 이미지: description CDATA img src
- 음식/생활용품/상품권 카테고리 필터링
- Naver lprice 비교 필터 적용 (clien.py 패턴 동일)
"""
import httpx
import re
import asyncio
import html
from bs4 import BeautifulSoup
from typing import Optional

RULIWEB_RSS_URL = "https://bbs.ruliweb.com/market/board/1020/rss"

# 스킵할 루리웹 카테고리
SKIP_CATEGORIES = {"음식", "생활용품", "상품권", "기타", "중고장터"}

# 비딜 키워드
INVALID_KEYWORDS = [
    "완료", "종료", "마감", "삭제", "광고", "공지", "이벤트",
    "모음", "일정모음", "라방", "끌올",
]


def _extract_retailer(title: str) -> tuple[str, str]:
    m = re.match(r'^\s*[\[\(【]([^\]）】]{1,20})[\]\)】]\s*', title)
    if m:
        retailer = m.group(1).strip()
        rest = title[m.end():].strip()
        return retailer, rest
    return "", title


def _clean_display_title(title: str) -> str:
    title = re.sub(r'[\(\（][^）\)]{0,60}(?:원|free|배송|\$)[^）\)]{0,30}[\)\）]', '', title, flags=re.IGNORECASE)
    title = re.sub(r'[\(\（][0-9,]+\s*원[\)\）]', '', title)
    title = re.sub(r'\[[^\]]{1,15}\]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def _extract_krw_price(title: str) -> Optional[int]:
    patterns = [
        r'[\(（\[]([0-9,]+)원[^\)）\]]{0,20}[\)）\]]',
        r'([0-9,]+)\s*원',
        r'₩\s*([0-9,]+)',
    ]
    for pattern in patterns:
        m = re.search(pattern, title)
        if m:
            try:
                price = int(m.group(1).replace(",", ""))
                if 500 <= price <= 50_000_000:
                    return price
            except Exception:
                continue
    return None


def _extract_usd_price(title: str) -> Optional[float]:
    m = re.search(r'\$\s*([0-9]+(?:\.[0-9]+)?)', title)
    if m:
        price = float(m.group(1))
        if 1.0 <= price <= 3000.0:
            return price
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


def _extract_image_from_description(desc_cdata: str) -> Optional[str]:
    """description CDATA에서 img src 추출"""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc_cdata)
    if m:
        return m.group(1)
    return None


def _parse_item(item) -> Optional[dict]:
    title_tag = item.find("title")
    if not title_tag:
        return None

    raw_title = title_tag.get_text(strip=True)

    # 비딜 키워드 필터
    if any(kw in raw_title for kw in INVALID_KEYWORDS):
        return None

    # 루리웹 카테고리 필터
    cat_tag = item.find("category")
    if cat_tag:
        ruli_cat = cat_tag.get_text(strip=True)
        if ruli_cat in SKIP_CATEGORIES:
            return None

    # 링크
    link_tag = item.find("link")
    link = ""
    if link_tag:
        if link_tag.string:
            link = link_tag.string.strip()
        else:
            ns = link_tag.next_sibling
            if ns:
                link = str(ns).strip()
    if not link or not link.startswith("http"):
        return None

    retailer, title_body = _extract_retailer(raw_title)
    display_title = _clean_display_title(title_body) or title_body[:80]

    krw_price = _extract_krw_price(raw_title)
    usd_price = None if krw_price else _extract_usd_price(raw_title)
    discount_rate = _extract_discount_rate(raw_title)

    # 이미지 (description CDATA)
    image_url = None
    desc_tag = item.find("description")
    if desc_tag:
        raw_desc = str(desc_tag)
        image_url = _extract_image_from_description(raw_desc)

    from app.services.categorizer import infer_category
    return {
        "raw_title": raw_title,
        "title": display_title,
        "retailer": retailer,
        "krw_price": krw_price,
        "usd_price": usd_price,
        "discount_rate": discount_rate or 0.0,
        "image_url": image_url,
        "ruliweb_url": link,
        "category": infer_category(display_title),
    }


async def _get_usd_krw_rate() -> float:
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json",
                timeout=5.0,
            )
            data = resp.json()
            rate = data["usd"]["krw"]
            if 1000 <= rate <= 2000:
                return float(rate)
    except Exception:
        pass
    return 1450.0


async def fetch_ruliweb_deals() -> list[dict]:
    """루리웹 핫딜 RSS → 파싱 → Naver enrichment"""
    from app.services.naver import search_product
    from app.services.community_enricher import is_food_or_daily, check_price_vs_naver

    usd_krw = await _get_usd_krw_rate()
    print(f"  [루리웹] USD/KRW: {usd_krw:.0f}")

    raw = []
    seen = set()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                RULIWEB_RSS_URL,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15.0,
                follow_redirects=True,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "xml")
            for item in soup.find_all("item"):
                d = _parse_item(item)
                if d and d["ruliweb_url"] not in seen:
                    if d["krw_price"] or d["usd_price"]:
                        seen.add(d["ruliweb_url"])
                        raw.append(d)
            print(f"  [루리웹] RSS {len(raw)}개 파싱 완료")
    except Exception as e:
        print(f"  [루리웹] RSS 오류: {e}")
        return []

    print(f"  [루리웹] Naver enrichment 시작 ({len(raw)}개)...")

    enriched = []
    for i in range(0, len(raw), 5):
        batch = raw[i:i+5]
        tasks = [search_product(d["title"]) for d in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for deal, nav in zip(batch, results):
            if isinstance(nav, Exception):
                nav = {}

            if is_food_or_daily(deal["title"], deal.get("category", "")):
                continue

            if deal["krw_price"]:
                sale_price = float(deal["krw_price"])
            elif deal["usd_price"]:
                sale_price = round(deal["usd_price"] * usd_krw / 100) * 100
            else:
                continue

            naver_check = await check_price_vs_naver(deal["title"], int(sale_price))
            await asyncio.sleep(0.2)
            if not naver_check["is_deal"]:
                import logging as _logging
                _logging.getLogger(__name__).info(
                    f"[루리웹] Naver lprice 필터 탈락: {deal['title'][:40]} | lprice={naver_check['lprice']:,} sale={int(sale_price):,}"
                )
                continue

            lprice = naver_check["lprice"]
            original_price = lprice if lprice > 0 else 0
            discount_rate = naver_check["discount_rate"]

            display_title = deal["title"]
            if deal["retailer"] and deal["retailer"] not in display_title:
                display_title = f"[{deal['retailer']}] {display_title}"

            enriched.append({
                "title": display_title,
                "description": None,
                "sale_price": sale_price,
                "original_price": original_price,
                "discount_rate": discount_rate,
                "image_url": nav.get("image_url") or deal.get("image_url"),
                "product_url": nav.get("product_url") or deal["ruliweb_url"],
                "source_post_url": deal["ruliweb_url"],
                "category": nav.get("naver_category") or deal["category"],
                "source": "community",
                "submitter_name": deal["retailer"] or "루리웹",
            })
        await asyncio.sleep(0.2)

    ok_img = sum(1 for d in enriched if d.get("image_url"))
    print(f"[루리웹] 완료: {len(enriched)}개 | 이미지: {ok_img}")
    return enriched
