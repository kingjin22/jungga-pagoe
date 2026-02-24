"""
클리앙 핫딜 RSS 파서
- 핫딜 게시판: https://www.clien.net/service/rss/hotdeal
- 제목 형식: [판매처] 상품명 (가격/배송) 또는 상품명 (가격)
- 이미지/상품URL: 네이버 쇼핑 API
- 식품/일상용품 필터, Naver lprice 비교 필터 적용
"""
import httpx
import re
import asyncio
import html
from bs4 import BeautifulSoup
from typing import Optional

CLIEN_RSS_URL = "https://www.clien.net/service/rss/hotdeal"

# 비딜 키워드 (제목에 포함 시 필터링)
INVALID_KEYWORDS = [
    "완료", "종료", "마감", "삭제", "광고", "공지", "이벤트",
    "잡담", "수다", "질문", "클리앙",
]


def _extract_retailer(title: str) -> tuple[str, str]:
    """[판매처] 태그 추출 → (retailer, title_without_prefix)"""
    m = re.match(r'^\s*[\[\(【]([^\]）】]{1,20})[\]\)】]\s*', title)
    if m:
        retailer = m.group(1).strip()
        rest = title[m.end():].strip()
        return retailer, rest
    return "", title


def _clean_display_title(title: str) -> str:
    """표시용 제목: 가격/배송/쇼핑몰 제거"""
    # (29,900원/무료배송), ($89.99/무료) 형태 제거
    title = re.sub(r'[\(\（][^）\)]{0,60}(?:원|free|배송|\$)[^）\)]{0,30}[\)\）]', '', title, flags=re.IGNORECASE)
    # (29,900원) 형태 제거
    title = re.sub(r'[\(\（][0-9,]+\s*원[\)\）]', '', title)
    # [삼카,비카] 같은 추가 태그 제거
    title = re.sub(r'\[[^\]]{1,15}\]', '', title)
    # 트리밍 + 연속공백
    title = re.sub(r'\s+', ' ', title).strip()
    return title or title


def _extract_krw_price(title: str) -> Optional[int]:
    patterns = [
        r'[\(（\[]([0-9,]+)원[^\)）\]]{0,20}[\)）\]]',  # (29,900원/무료배송)
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
    # 숫자+쉼표 패턴: (29,620/무료) 같은 형식
    m = re.search(r'[\(\[\s]([1-9][0-9,]{2,9})\s*[\(（\[/,]', title)
    if m:
        try:
            price = int(m.group(1).replace(",", ""))
            if 500 <= price <= 5_000_000:
                return price
        except Exception:
            pass
    return None


def _extract_usd_price(title: str) -> Optional[float]:
    """달러 가격 추출: $89.99, ($89.99/무료) 등"""
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


def _is_free_deal(title: str) -> bool:
    """진짜 무료 딜 판별 (배송무료와 구별)"""
    # (무료/무료) 패턴
    if re.search(r'[\(（](무료)\s*/\s*(무료)[\)）]', title):
        return True
    # $0
    if re.search(r'\$\s*0(?:\.0+)?\s*[/\)]', title):
        return True
    return False


async def _get_usd_krw_rate() -> float:
    """실시간 USD/KRW 환율 (실패 시 1450 fallback)"""
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


def _parse_item(item) -> Optional[dict]:
    title_tag = item.find("title")
    if not title_tag:
        return None

    raw_title = title_tag.get_text(strip=True)

    # 비딜 키워드 필터
    if any(kw in raw_title for kw in INVALID_KEYWORDS):
        return None

    # 끌올 제거
    clean = re.sub(r'^\s*[\(（\[【]?\s*(끌올)\s*[\)）\]】]?\s*', '', raw_title, flags=re.IGNORECASE).strip()
    if not clean:
        return None

    # 링크 추출 — 클리앙 RSS는 <link> 태그가 CDATA 또는 next_sibling일 수 있음
    link = ""
    link_tag = item.find("link")
    if link_tag:
        # BeautifulSoup xml 파서에서 <link>는 next_sibling에 텍스트가 오는 경우가 많음
        if link_tag.string:
            link = link_tag.string.strip()
        else:
            # next_sibling이 NavigableString인 경우
            ns = link_tag.next_sibling
            if ns:
                link = str(ns).strip()

    # guid로 fallback
    if not link or not link.startswith("http"):
        guid_tag = item.find("guid")
        if guid_tag:
            link = guid_tag.get_text(strip=True)

    if not link or not link.startswith("http"):
        return None

    # 리테일러 추출
    retailer, title_body = _extract_retailer(clean)
    if not title_body:
        title_body = clean

    # 표시 제목 (깔끔하게)
    display_title = _clean_display_title(title_body)
    if not display_title:
        display_title = title_body[:80]

    # 가격 추출
    krw_price = _extract_krw_price(clean)
    usd_price = None
    if not krw_price:
        usd_price = _extract_usd_price(clean)

    # 무료 딜
    is_free = _is_free_deal(clean) and not krw_price and not usd_price

    discount_rate = _extract_discount_rate(clean)

    # description
    description = ""
    desc_tag = item.find("description")
    if desc_tag:
        raw = desc_tag.get_text(separator=" ", strip=True)
        raw = html.unescape(raw)
        raw = re.sub(r'[\s\xa0]+', ' ', raw).strip()
        description = raw[:200]

    from app.services.categorizer import infer_category
    return {
        "raw_title": clean,
        "title": display_title,
        "retailer": retailer,
        "description": description or None,
        "krw_price": krw_price,
        "usd_price": usd_price,
        "is_free": is_free,
        "discount_rate": discount_rate or 0.0,
        "clien_url": link,
        "category": infer_category(display_title),
    }


async def fetch_clien_deals() -> list[dict]:
    """
    클리앙 핫딜 RSS → 파싱 → 네이버 쇼핑 이미지/URL enrichment
    """
    from app.services.naver import search_product
    from app.services.community_enricher import is_food_or_daily, check_price_vs_naver

    # 환율 가져오기
    usd_krw = await _get_usd_krw_rate()
    print(f"  [클리앙] USD/KRW: {usd_krw:.0f}")

    raw = []
    seen = set()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                CLIEN_RSS_URL,
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15.0,
                follow_redirects=True,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "xml")
            for item in soup.find_all("item"):
                d = _parse_item(item)
                if d and d["clien_url"] not in seen:
                    # 가격 있는 것만 수집
                    if d["krw_price"] or d["usd_price"] or d["is_free"]:
                        seen.add(d["clien_url"])
                        raw.append(d)
            print(f"  [클리앙] RSS {len(raw)}개 파싱 완료")
    except Exception as e:
        print(f"  [클리앙] RSS 오류: {e}")
        return []

    print(f"  [클리앙] 네이버 enrichment 시작 ({len(raw)}개)...")

    # 네이버 쇼핑 API enrichment (5개씩 병렬)
    enriched = []
    for i in range(0, len(raw), 5):
        batch = raw[i:i+5]
        tasks = [search_product(d["title"]) for d in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for deal, nav in zip(batch, results):
            if isinstance(nav, Exception):
                nav = {}

            # 식품/일상용품 필터
            if is_food_or_daily(deal["title"], deal.get("category", "")):
                continue

            # 가격 확정
            if deal["is_free"]:
                sale_price = 0.0
            elif deal["krw_price"]:
                sale_price = float(deal["krw_price"])
            elif deal["usd_price"]:
                sale_price = round(deal["usd_price"] * usd_krw / 100) * 100
            else:
                continue

            # Naver lprice 비교 필터 (is_free 딜은 스킵)
            original_price = 0
            discount_rate = 0
            if not deal["is_free"] and sale_price > 0:
                naver_check = await check_price_vs_naver(deal["title"], int(sale_price))
                await asyncio.sleep(0.2)
                if not naver_check["is_deal"]:
                    import logging as _logging
                    _logging.getLogger(__name__).info(
                        f"[클리앙] Naver lprice 필터 탈락: {deal['title'][:40]} | lprice={naver_check['lprice']:,} sale={int(sale_price):,}"
                    )
                    continue
                lprice = naver_check["lprice"]
                if lprice > 0:
                    original_price = lprice
                    discount_rate = naver_check["discount_rate"]

            # 표시 제목: retailer 있으면 앞에 붙임
            display_title = deal["title"]
            if deal["retailer"] and deal["retailer"] not in display_title:
                display_title = f"[{deal['retailer']}] {display_title}"

            naver_img = nav.get("image_url")

            enriched.append({
                "title": display_title,
                "description": deal["description"],
                "sale_price": sale_price,
                "original_price": original_price,
                "discount_rate": discount_rate,
                "image_url": naver_img,
                "product_url": nav.get("product_url") or deal["clien_url"],
                "source_post_url": deal["clien_url"],   # 원글 URL (만료 감지용)
                "category": nav.get("naver_category") or deal["category"],
                "source": "community",
                "submitter_name": deal["retailer"] or "클리앙",
            })
        await asyncio.sleep(0.2)

    ok_img = sum(1 for d in enriched if d.get("image_url"))
    free = sum(1 for d in enriched if d["sale_price"] == 0)
    print(f"[클리앙] 완료: {len(enriched)}개 | 이미지: {ok_img} | 무료: {free}")
    return enriched
