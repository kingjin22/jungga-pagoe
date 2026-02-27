"""
어미새 인기정보 RSS 파서 (eomisae.co.kr)
- 인기정보 게시판: https://eomisae.co.kr/rss?mid=fs
- 제목에 가격 직접 포함: "지이크 수트 201,070원", "￦3,430", "1.2만원" 등
- 카테고리: 패션국내, 패션해외, 기타국내, 네이버 등
- dc:creator 태그로 작성자 이름 추출
"""
import httpx
import re
import asyncio
import html
from bs4 import BeautifulSoup
from typing import Optional

EOMISAE_RSS_URL = "https://eomisae.co.kr/rss?mid=fs"

# 스킵할 카테고리 (두 번째 <category> 태그 값)
SKIP_CATEGORIES = {
    "기타국내",       # 식품/생활용품이 많음
    "기타해외",       # 건강식품/보충제 위주
    "이벤트",         # 포인트/쿠폰 이벤트
    "이벤트:쿠폰",
    "포인트",
    "잡담",
    # "패션게시판",   # 일반 패션 얘기, 딜 아님 — 가격 없으면 어차피 필터됨
}

# 비딜 키워드 (제목에 포함 시 필터링)
INVALID_KEYWORDS = [
    "완료", "종료", "마감", "삭제", "광고", "공지",
    "잡담", "수다", "질문",
]


def _extract_krw_price(title: str) -> Optional[int]:
    """
    한국 원화 가격 추출
    - "201,070원" → 201070
    - "￦3,430"   → 3430
    - "₩3,430"   → 3430
    - "1.2만원"   → 12000
    - "3만원"     → 30000
    - "2.2발"     → 22000 ('발' = 만원 단위 은어)
    """
    # 만원 단위: "1.2만원", "3만원", "1만원"
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*만\s*원', title)
    if m:
        try:
            price = round(float(m.group(1)) * 10000)
            if 500 <= price <= 50_000_000:
                return price
        except Exception:
            pass

    # 어미새 속어 "발" = 만원: "2.2발", "3발"
    m = re.search(r'([0-9]+(?:\.[0-9]+)?)\s*발\b', title)
    if m:
        try:
            price = round(float(m.group(1)) * 10000)
            if 500 <= price <= 5_000_000:
                return price
        except Exception:
            pass

    # ￦기호 or ₩기호
    m = re.search(r'[￦₩]\s*([0-9,]+)', title)
    if m:
        try:
            price = int(m.group(1).replace(",", ""))
            if 500 <= price <= 50_000_000:
                return price
        except Exception:
            pass

    # 괄호 안 가격: (29,900원/무료배송)
    m = re.search(r'[\(（\[][0-9,]+\s*원[^\)）\]]{0,20}[\)）\]]', title)
    if m:
        inner = m.group(0)
        n = re.search(r'([0-9,]+)\s*원', inner)
        if n:
            try:
                price = int(n.group(1).replace(",", ""))
                if 500 <= price <= 50_000_000:
                    return price
            except Exception:
                pass

    # 일반 숫자+원: "3,500원", "9.900원" (온점 천 단위 구분자도 처리)
    for pattern in [
        r'([0-9]{1,3}(?:[,\.][0-9]{3})+)\s*원',  # 3자리 구분 천단위 (쉼표 or 온점)
        r'([0-9,]+)\s*원',
    ]:
        m = re.search(pattern, title)
        if m:
            raw = m.group(1).replace(",", "").replace(".", "")
            try:
                price = int(raw)
                if 500 <= price <= 50_000_000:
                    return price
            except Exception:
                continue

    return None


def _extract_usd_price(title: str) -> Optional[float]:
    """달러 가격 추출: $89.99"""
    m = re.search(r'\$\s*([0-9]+(?:\.[0-9]+)?)', title)
    if m:
        price = float(m.group(1))
        if 1.0 <= price <= 3000.0:
            return price
    return None


def _extract_discount_rate(title: str) -> Optional[float]:
    m = re.search(r'(\d{1,2})\s*%\s*(?:할인|off|세일)', title, re.IGNORECASE)
    if m:
        rate = float(m.group(1))
        if 5 <= rate <= 95:
            return rate
    if "반값" in title:
        return 50.0
    return None


def _clean_display_title(title: str) -> str:
    """표시용 제목: 가격/배송/수량 관련 표현 제거"""
    # (29,900원/무료배송) 형태 제거
    title = re.sub(r'[\(\（][^）\)]{0,60}(?:원|free|배송|\$)[^）\)]{0,30}[\)\）]', '', title, flags=re.IGNORECASE)
    # (29,900원) 형태 제거
    title = re.sub(r'[\(\（][0-9,]+\s*원[\)\）]', '', title)
    # "/ ￦3,430" 형태 제거
    title = re.sub(r'/\s*[￦₩]\s*[0-9,]+', '', title)
    # "3,500원", "1.2만원" 가격 표현 제거
    title = re.sub(r'[0-9,]+(?:\.[0-9]+)?\s*만\s*원', '', title)
    title = re.sub(r'[0-9]{1,3}(?:[,\.][0-9]{3})+\s*원', '', title)
    title = re.sub(r'[0-9]+\s*원', '', title)
    title = re.sub(r'[￦₩]\s*[0-9,]+', '', title)
    # "[N개, N팩]" 형태 제거
    title = re.sub(r'\[[^\]]{1,15}\]', '', title)
    # 연속 공백 및 트리밍
    title = re.sub(r'\s+', ' ', title).strip()
    # 끝에 / 제거
    title = re.sub(r'\s*/\s*$', '', title).strip()
    return title


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

    # 카테고리 추출 (두 번째 <category> = 실제 게시판)
    cats = item.find_all("category")
    board_cat = ""
    if len(cats) >= 2:
        board_cat = cats[1].get_text(strip=True)
    elif len(cats) == 1:
        board_cat = cats[0].get_text(strip=True)

    # 스킵 카테고리 확인
    if board_cat in SKIP_CATEGORIES:
        return None

    # 링크 추출
    link = ""
    link_tag = item.find("link")
    if link_tag:
        if link_tag.string:
            link = link_tag.string.strip()
        else:
            ns = link_tag.next_sibling
            if ns:
                link = str(ns).strip()

    if not link or not link.startswith("http"):
        guid_tag = item.find("guid")
        if guid_tag:
            link = guid_tag.get_text(strip=True)

    if not link or not link.startswith("http"):
        return None

    # 작성자 추출 (dc:creator)
    creator = "어미새"
    creator_tag = item.find("dc:creator") or item.find("creator")
    if creator_tag:
        creator_text = creator_tag.get_text(strip=True)
        if creator_text:
            creator = creator_text

    # 가격 추출
    krw_price = _extract_krw_price(raw_title)
    usd_price = None
    if not krw_price:
        usd_price = _extract_usd_price(raw_title)

    discount_rate = _extract_discount_rate(raw_title)

    # 표시 제목 (가격 제거)
    display_title = _clean_display_title(raw_title)
    if not display_title:
        display_title = raw_title[:80]

    # description
    description = ""
    desc_tag = item.find("description")
    if desc_tag:
        raw = desc_tag.get_text(separator=" ", strip=True)
        raw = html.unescape(raw)
        raw = re.sub(r'[\s\xa0]+', ' ', raw).strip()
        # URL만 있는 description은 무시
        if not re.match(r'^https?://', raw):
            description = raw[:200]

    from app.services.categorizer import infer_category
    return {
        "raw_title": raw_title,
        "title": display_title,
        "board_category": board_cat,
        "description": description or None,
        "krw_price": krw_price,
        "usd_price": usd_price,
        "discount_rate": discount_rate or 0.0,
        "eomisae_url": link,
        "submitter_name": creator,
        "category": infer_category(display_title),
    }


async def fetch_eomisae_deals() -> list[dict]:
    """
    어미새 인기정보 RSS → 파싱 → 네이버 쇼핑 이미지/URL enrichment
    """
    from app.services.naver import search_product
    from app.services.community_enricher import is_food_or_daily, check_price_vs_naver

    # 환율 가져오기
    usd_krw = await _get_usd_krw_rate()
    print(f"  [어미새] USD/KRW: {usd_krw:.0f}")

    raw = []
    seen = set()

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                EOMISAE_RSS_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                },
                timeout=15.0,
                follow_redirects=True,
            )
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "xml")
            for item in soup.find_all("item"):
                d = _parse_item(item)
                if d and d["eomisae_url"] not in seen:
                    # 가격 있는 것만 수집
                    if d["krw_price"] or d["usd_price"]:
                        seen.add(d["eomisae_url"])
                        raw.append(d)
            print(f"  [어미새] RSS {len(raw)}개 가격 있는 항목 파싱 완료")
    except Exception as e:
        print(f"  [어미새] RSS 오류: {e}")
        return []

    print(f"  [어미새] 네이버 enrichment 시작 ({len(raw)}개)...")

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
            if deal["krw_price"]:
                sale_price = float(deal["krw_price"])
            elif deal["usd_price"]:
                sale_price = round(deal["usd_price"] * usd_krw / 100) * 100
            else:
                continue

            if sale_price <= 0:
                continue

            # Naver lprice 비교 필터
            original_price = 0
            discount_rate = 0
            naver_check = await check_price_vs_naver(deal["title"], int(sale_price))
            await asyncio.sleep(0.2)
            if not naver_check["is_deal"]:
                import logging as _logging
                _logging.getLogger(__name__).info(
                    f"[어미새] Naver lprice 필터 탈락: {deal['title'][:40]} | lprice={naver_check['lprice']:,} sale={int(sale_price):,}"
                )
                continue
            lprice = naver_check["lprice"]
            if lprice > 0:
                original_price = lprice
                discount_rate = naver_check["discount_rate"]

            naver_img = nav.get("image_url") if isinstance(nav, dict) else None

            enriched.append({
                "title": deal["title"],
                "description": deal["description"],
                "sale_price": sale_price,
                "original_price": original_price,
                "discount_rate": discount_rate,
                "image_url": naver_img,
                "product_url": nav.get("product_url") if isinstance(nav, dict) else deal["eomisae_url"],
                "source_post_url": deal["eomisae_url"],
                "category": (nav.get("naver_category") if isinstance(nav, dict) else None) or deal["category"],
                "source": "community",
                "submitter_name": deal["submitter_name"],
            })
        await asyncio.sleep(0.2)

    ok_img = sum(1 for d in enriched if d.get("image_url"))
    print(f"[어미새] 완료: {len(enriched)}개 | 이미지: {ok_img}")
    return enriched
