"""
뽐뿌 RSS 파서
- 국내 딜: 원화 가격 추출
- 해외 딜: 달러 가격 → KRW 변환 (실시간 환율)
- 이미지/상품URL: 네이버 쇼핑 API
- 표시 제목: 쇼핑몰 태그/가격 제거한 순수 상품명
"""
import httpx
import re
import asyncio
import html
from bs4 import BeautifulSoup
from typing import Optional

RSS_URLS = {
    "ppomppu": "https://www.ppomppu.co.kr/rss.php?id=ppomppu",
    # 해외 딜 비활성화: 영문 제목 → 네이버 enrichment가 엉뚱한 한국 제품 매칭 → 가격/이미지 전부 틀림
    # "ppomppu_foreign": "https://www.ppomppu.co.kr/rss.php?id=ppomppu4",
}

INVALID_KEYWORDS = ["완료", "종료", "마감", "삭제", "광고", "공지", "이벤트"]


def _extract_retailer(title: str) -> tuple[str, str]:
    """[쇼핑몰명] 태그 추출 → (retailer, title_without_prefix)"""
    m = re.match(r'^\s*[\[\(【]([^\]）】]{1,20})[\]\)】]\s*', title)
    if m:
        retailer = m.group(1).strip()
        rest = title[m.end():].strip()
        return retailer, rest
    return "", title


def _clean_display_title(title: str) -> str:
    """표시용 제목: 가격/배송/쇼핑몰 제거"""
    # (11,910원/무료), (14,900원), ($18/free) 제거
    title = re.sub(r'[\(\（][^）\)]{0,50}(?:원|free|배송)[^）\)]{0,20}[\)\）]', '', title, flags=re.IGNORECASE)
    # [삼카,비카] 같은 추가 태그 제거
    title = re.sub(r'\[[^\]]{1,15}\]', '', title)
    # 트리밍 + 연속공백
    title = re.sub(r'\s+', ' ', title).strip()
    return title or title  # 빈 경우 원본 반환


def _extract_krw_price(title: str) -> Optional[int]:
    patterns = [
        r'[\(（\[]([0-9,]+)원[^\)）\]]{0,15}[\)）\]]',  # (11,910원/무료) or [29,620원/무료]
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
    # 숫자+쉼표 패턴: [29,620(삼카)/무료] 같은 형식
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
    """달러 가격 추출: $18.9, ($14.4/free) 등"""
    m = re.search(r'\$\s*([0-9]+(?:\.[0-9]+)?)', title)
    if m:
        price = float(m.group(1))
        if 1.0 <= price <= 3000.0:  # 3000달러 이하만
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
    """
    진짜 무료 딜 판별 (배송무료와 구별)
    - (무료/무료): 가격도 무료 = 진짜 무료
    - ($0/free): 달러 0 = 무료
    - [에픽게임즈] 게임 무료 배포
    - NOT: (X원/무료), ($X/free) — 가격 있는 것의 배송무료
    """
    # (무료/무료) or (무료) 패턴
    if re.search(r'[\(（](무료)\s*/\s*(무료)[\)）]', title):
        return True
    # $0
    if re.search(r'\$\s*0(?:\.0+)?\s*[/\)]', title):
        return True
    # 에픽게임즈 무료 배포
    if "에픽게임즈" in title and "무료" in title:
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


def _parse_item(item, is_foreign: bool = False) -> Optional[dict]:
    title_tag = item.find("title")
    link_tag = item.find("link")
    desc_tag = item.find("description")

    if not title_tag or not link_tag:
        return None

    raw_title = title_tag.get_text(strip=True)

    # 상태 이상 딜 제거
    if any(kw in raw_title for kw in INVALID_KEYWORDS):
        return None
    # 끌올 처리 (제목은 유지)
    clean = re.sub(r'^\s*[\(（\[【]?\s*(끌올)\s*[\)）\]】]?\s*', '', raw_title, flags=re.IGNORECASE).strip()
    if not clean:
        return None

    link = link_tag.get_text(strip=True) if link_tag.string else str(link_tag.next_sibling or "").strip()
    if not link.startswith("http"):
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
    usd_price = None
    krw_price = _extract_krw_price(clean)

    if not krw_price and is_foreign:
        usd_price = _extract_usd_price(clean)
        # usd_price는 나중에 환율 적용 (placeholder 저장)

    # 무료 딜 (0원)
    is_free = _is_free_deal(clean) and not krw_price and not usd_price

    discount_rate = _extract_discount_rate(clean)

    description = ""
    if desc_tag:
        raw = desc_tag.get_text(separator=" ", strip=True)
        raw = html.unescape(raw)
        raw = re.sub(r'[\s\xa0]+', ' ', raw).strip()
        description = raw[:200]

    from app.services.categorizer import infer_category
    return {
        "raw_title": clean,          # 원본 (뽐뿌 제목 그대로)
        "title": display_title,      # 표시용 (깔끔한 상품명)
        "retailer": retailer,
        "description": description or None,
        "krw_price": krw_price,
        "usd_price": usd_price,
        "is_free": is_free,
        "discount_rate": discount_rate or 0.0,
        "ppomppu_url": link,
        "category": infer_category(display_title),
        "is_foreign": is_foreign,
    }


async def fetch_ppomppu_deals() -> list[dict]:
    """
    뽐뿌 RSS → 파싱 → 네이버 쇼핑 이미지/URL enrichment
    """
    from app.services.naver import search_product

    # 환율 가져오기
    usd_krw = await _get_usd_krw_rate()
    print(f"  USD/KRW: {usd_krw:.0f}")

    raw = []
    seen = set()

    async with httpx.AsyncClient() as client:
        for name, url in RSS_URLS.items():
            is_foreign = "foreign" in name
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15.0, follow_redirects=True)
                resp.raise_for_status()
                soup = BeautifulSoup(resp.text, "xml")
                batch_before = len(raw)
                for item in soup.find_all("item"):
                    d = _parse_item(item, is_foreign=is_foreign)
                    if d and d["ppomppu_url"] not in seen:
                        # 가격 있는 것만 수집
                        if d["krw_price"] or d["usd_price"] or d["is_free"]:
                            seen.add(d["ppomppu_url"])
                            raw.append(d)
                print(f"  [뽐뿌/{name}] +{len(raw)-batch_before}개 (총 {len(raw)})")
            except Exception as e:
                print(f"  [뽐뿌/{name}] 오류: {e}")

    print(f"  네이버 enrichment 시작 ({len(raw)}개)...")

    # 네이버 쇼핑 API enrichment (5개씩 병렬)
    enriched = []
    for i in range(0, len(raw), 5):
        batch = raw[i:i+5]
        # 해외 딜은 영문 제목으로 검색 (retailer 제거)
        search_queries = [d["title"] for d in batch]
        tasks = [search_product(q) for q in search_queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for deal, nav in zip(batch, results):
            if isinstance(nav, Exception):
                nav = {}

            # 가격 확정
            if deal["is_free"]:
                sale_price = 0.0
                orig_price = 0.0
                dr = 100.0
            elif deal["krw_price"]:
                sale_price = float(deal["krw_price"])
                dr = deal["discount_rate"]
                orig_price = round(sale_price / (1 - dr / 100)) if dr > 0 else sale_price
            elif deal["usd_price"]:
                sale_price = round(deal["usd_price"] * usd_krw / 100) * 100  # 백원 단위 반올림
                dr = deal["discount_rate"]
                orig_price = sale_price
            else:
                continue

            # 표시 제목: retailer 있으면 앞에 붙임
            display_title = deal["title"]
            if deal["retailer"] and deal["retailer"] not in display_title:
                display_title = f"[{deal['retailer']}] {display_title}"

            enriched.append({
                "title": display_title,
                "description": deal["description"],
                "sale_price": sale_price,
                "original_price": orig_price,
                "discount_rate": dr,
                "image_url": nav.get("image_url"),
                "product_url": nav.get("product_url") or deal["ppomppu_url"],
                "ppomppu_url": deal["ppomppu_url"],  # 실제 쇼핑몰 URL 추출용
                "category": nav.get("naver_category") or deal["category"],
                "source": "community",
                "submitter_name": deal["retailer"] or "뽐뿌",
                "is_foreign": deal["is_foreign"],
            })
        await asyncio.sleep(0.2)

    ok_img = sum(1 for d in enriched if d.get("image_url"))
    foreign = sum(1 for d in enriched if d.get("is_foreign"))
    free = sum(1 for d in enriched if d["sale_price"] == 0)
    print(f"[뽐뿌] 완료: {len(enriched)}개 | 이미지: {ok_img} | 해외: {foreign} | 무료: {free}")
    return enriched
