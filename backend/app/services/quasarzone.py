"""
퀘이사존 핫딜 HTML 스크래퍼
- 핫딜 게시판: https://quasarzone.com/bbs/qb_saleinfo
- 제목 형식: [판매처] 상품명
- 카테고리: PC/하드웨어, 모바일/태블릿, 생활/식품 등
- 가격: ￦ 12,210 (KRW) 형식 파싱
- 식품/생활용품 카테고리 자동 필터링
- Naver lprice 비교 필터 적용
"""
import httpx
import re
import asyncio
from bs4 import BeautifulSoup
from typing import Optional

QUASARZONE_BOARD_URL = "https://quasarzone.com/bbs/qb_saleinfo"
BASE_URL = "https://quasarzone.com"

# 퀘이사존 스킵 카테고리 (식품/생활 계열)
SKIP_CATEGORIES = {
    "생활/식품", "생활용품", "식품", "식품/음료", "음식",
    "상품권/기타", "상품권", "기타",
}

# 비딜 키워드
INVALID_KEYWORDS = [
    "완료", "종료", "마감", "삭제", "광고", "공지", "이벤트",
    "모음", "잡담", "수다",
]

# 진행 중 상태 키워드
ACTIVE_STATUS = {"진행중", "진행 중"}


def _extract_retailer(title: str) -> tuple[str, str]:
    """[판매처] 태그 추출"""
    m = re.match(r'^\s*[\[\(【]([^\]）】]{1,20})[\]\)】]\s*', title)
    if m:
        retailer = m.group(1).strip()
        rest = title[m.end():].strip()
        return retailer, rest
    return "", title


def _clean_display_title(title: str) -> str:
    """표시용 제목 정제"""
    title = re.sub(r'[\(\（][^）\)]{0,60}(?:원|free|배송|\$)[^）\)]{0,30}[\)\）]', '', title, flags=re.IGNORECASE)
    title = re.sub(r'[\(\（][0-9,]+\s*원[\)\）]', '', title)
    title = re.sub(r'\[[^\]]{1,15}\]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def _parse_krw_price(price_text: str) -> Optional[int]:
    """￦ 12,210 (KRW) 형식에서 가격 추출"""
    m = re.search(r'([0-9,]+)', price_text.replace('￦', '').replace('₩', ''))
    if m:
        try:
            price = int(m.group(1).replace(',', ''))
            if 500 <= price <= 50_000_000:
                return price
        except Exception:
            pass
    return None


def _extract_usd_price(price_text: str) -> Optional[float]:
    """$ 89.99 형식에서 달러 가격 추출"""
    m = re.search(r'\$\s*([0-9]+(?:\.[0-9]+)?)', price_text)
    if m:
        price = float(m.group(1))
        if 1.0 <= price <= 3000.0:
            return price
    return None


def _parse_item(div) -> Optional[dict]:
    """div.market-info-list 파싱"""
    # 제목 링크
    subject_a = div.select_one('a.subject-link')
    if not subject_a:
        return None

    href = subject_a.get('href', '')
    if not href or 'qb_saleinfo/views' not in href:
        return None
    link = BASE_URL + href if href.startswith('/') else href

    # 제목 텍스트
    title_span = subject_a.select_one('span.ellipsis-with-reply-cnt')
    raw_title = (title_span.get_text(strip=True) if title_span else subject_a.get_text(strip=True))
    if not raw_title:
        return None

    # 비딜 키워드 필터
    if any(kw in raw_title for kw in INVALID_KEYWORDS):
        return None

    # 진행 상태
    label_span = div.select_one('span.label')
    status = label_span.get_text(strip=True) if label_span else ""
    if status and status not in ACTIVE_STATUS:
        return None  # 종료/완료 딜 제외

    # 카테고리
    cat_span = div.select_one('span.category')
    category_raw = cat_span.get_text(strip=True) if cat_span else ""
    if category_raw in SKIP_CATEGORIES:
        return None

    # 가격 파싱 — span.text-orange 에 가격 표시됨
    price_span = div.select_one('span.text-orange')
    price_text = price_span.get_text(strip=True) if price_span else ""

    krw_price = None
    usd_price = None

    if price_text:
        if '￦' in price_text or 'KRW' in price_text or '원' in price_text:
            krw_price = _parse_krw_price(price_text)
        elif '$' in price_text or 'USD' in price_text:
            usd_price = _extract_usd_price(price_text)
        else:
            krw_price = _parse_krw_price(price_text)

    # 가격 없으면 제외
    if not krw_price and not usd_price:
        return None

    # 썸네일 이미지
    image_url = None
    thumb_img = div.select_one('div.thumb-wrap img.maxImg')
    if thumb_img:
        src = thumb_img.get('src', '')
        if src and src.startswith('http'):
            image_url = src
    if not image_url:
        thumb_span = div.select_one('div.thumb-wrap span.img-background-wrap')
        if thumb_span:
            style = thumb_span.get('style', '')
            m = re.search(r'url\(["\']?([^"\')\s]+)["\']?\)', style)
            if m:
                image_url = m.group(1).rstrip('?')

    # 리테일러 추출
    retailer, title_body = _extract_retailer(raw_title)
    display_title = _clean_display_title(title_body) or title_body[:80]

    from app.services.categorizer import infer_category
    return {
        "raw_title": raw_title,
        "title": display_title,
        "retailer": retailer,
        "krw_price": krw_price,
        "usd_price": usd_price,
        "image_url": image_url,
        "quasarzone_url": link,
        "category": infer_category(display_title) or category_raw,
    }


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


async def fetch_quasarzone_deals() -> list[dict]:
    """퀘이사존 핫딜 HTML 스크래핑 → Naver enrichment"""
    from app.services.naver import search_product
    from app.services.community_enricher import is_food_or_daily, check_price_vs_naver

    usd_krw = await _get_usd_krw_rate()
    print(f"  [퀘이사존] USD/KRW: {usd_krw:.0f}")

    raw = []
    seen = set()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                QUASARZONE_BOARD_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                                  "Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
                },
                timeout=20.0,
                follow_redirects=True,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            deal_divs = soup.find_all("div", class_="market-info-list")
            for div in deal_divs:
                d = _parse_item(div)
                if d and d["quasarzone_url"] not in seen:
                    seen.add(d["quasarzone_url"])
                    raw.append(d)

            print(f"  [퀘이사존] HTML {len(raw)}개 파싱 완료 (전체 div: {len(deal_divs)}개)")
    except Exception as e:
        print(f"  [퀘이사존] 스크래핑 오류: {e}")
        return []

    print(f"  [퀘이사존] Naver enrichment 시작 ({len(raw)}개)...")

    enriched = []
    for i in range(0, len(raw), 5):
        batch = raw[i:i + 5]
        tasks = [search_product(d["title"]) for d in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for deal, nav in zip(batch, results):
            if isinstance(nav, Exception):
                nav = {}

            # 식품/일상용품 필터
            if is_food_or_daily(deal["title"], deal.get("category", "")):
                continue

            # 가격 확정
            if deal["krw_price"]:
                sale_price = float(deal["krw_price"])
            elif deal["usd_price"]:
                sale_price = round(deal["usd_price"] * usd_krw / 100) * 100
            else:
                continue

            # Naver lprice 비교 필터
            naver_check = await check_price_vs_naver(deal["title"], int(sale_price))
            await asyncio.sleep(0.2)
            if not naver_check["is_deal"]:
                import logging as _logging
                _logging.getLogger(__name__).info(
                    f"[퀘이사존] Naver lprice 필터 탈락: {deal['title'][:40]} "
                    f"| lprice={naver_check['lprice']:,} sale={int(sale_price):,}"
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
                "product_url": nav.get("product_url") or deal["quasarzone_url"],
                "source_post_url": deal["quasarzone_url"],
                "category": nav.get("naver_category") or deal["category"],
                "source": "community",
                "submitter_name": deal["retailer"] or "퀘이사존",
            })
        await asyncio.sleep(0.2)

    ok_img = sum(1 for d in enriched if d.get("image_url"))
    print(f"[퀘이사존] 완료: {len(enriched)}개 | 이미지: {ok_img}")
    return enriched
