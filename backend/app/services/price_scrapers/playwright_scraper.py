"""
실시간 쇼핑몰 가격 크롤러 (Playwright 기반)

지원 쇼핑몰: 지마켓, 옥션, 11번가, 롯데온, 쿠팡, 스마트스토어, SSG

핵심 용도:
- 커뮤니티 딜 수집 시 실제 쇼핑몰 현재가 검증
- 핫딜 소진(가격 정상화) 즉시 감지
"""
import re
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

SOLD_OUT_TEXTS = ["품절", "일시품절", "판매종료", "Sold Out", "품절입니다", "재고 없음", "구매불가"]


@dataclass
class PriceResult:
    price: int
    original_price: int
    in_stock: bool
    retailer: str
    url: str

    def __bool__(self):
        return self.in_stock and self.price > 0


def normalize_retailer_url(url: str) -> Optional[str]:
    """
    ppomppu 포스트에서 뽑은 쇼핑몰 URL을 직접 접근 가능한 URL로 변환.

    - 지마켓 affiliate(link.gmarket) → item.gmarket 직접 URL
    - 옥션 affiliate(link.auction) → itempage3.auction 직접 URL
    - 11번가 gateway(Gateway.tmall?lpUrl=...) → products/{prdNo}
    - 쿠팡 affiliate → pageKey 추출 → coupang.com/vp/products/
    - 나머지는 그대로
    """
    if not url:
        return None

    # 지마켓 affiliate → direct
    m = re.search(r'item-no=(\d+)', url)
    if m and "gmarket.co.kr" in url:
        return f"https://item.gmarket.co.kr/Item?goodscode={m.group(1)}"

    # 옥션 affiliate → direct
    m2 = re.search(r'item-no=([A-Za-z0-9]+)', url)
    if m2 and "auction.co.kr" in url:
        return f"https://itempage3.auction.co.kr/DetailView.aspx?ItemNo={m2.group(1)}"

    # 11번가 gateway URL → products URL
    if "11st.co.kr" in url and "Gateway" in url:
        # prdNo 추출
        m3 = re.search(r'prdNo=(\d+)', url)
        if m3:
            return f"https://www.11st.co.kr/products/{m3.group(1)}"

    # 쿠팡 affiliate → products URL
    if "link.coupang.com" in url:
        m4 = re.search(r'pageKey=(\d+)', url)
        if m4:
            return f"https://www.coupang.com/vp/products/{m4.group(1)}"

    return url  # 나머지는 그대로


def extract_retailer_links_from_page(links: list) -> Optional[str]:
    """
    Playwright page.evaluate로 얻은 href 리스트에서 쇼핑몰 URL 추출.
    우선순위: 직접 쇼핑몰 URL > affiliate URL
    """
    PRIORITY_PATTERNS = [
        # 직접 URL (우선)
        (r'https?://item\.gmarket\.co\.kr/Item\?goodscode=\d+', "gmarket"),
        (r'https?://itempage3\.auction\.co\.kr/DetailView', "auction"),
        (r'https?://www\.11st\.co\.kr/products/\d+', "11번가"),
        (r'https?://(?:www\.|m\.)?lotteon\.com/p/product/[A-Z0-9]+', "롯데온"),
        (r'https?://www\.coupang\.com/vp/products/\d+', "쿠팡"),
        (r'https?://smartstore\.naver\.com/[^/\s]+/products/\d+', "스마트스토어"),
        (r'https?://(?:www\.|dept\.)?ssg\.com/item/itemView', "SSG"),
        # affiliate URL (차선)
        (r'https?://link\.gmarket\.co\.kr/gate/pcs\?item-no=\d+', "gmarket-aff"),
        (r'https?://link\.auction\.co\.kr/gate/pcs\?item-no=[A-Za-z0-9]+', "auction-aff"),
        (r'https?://(?:www\.|m\.)?11st\.co\.kr/connect/Gateway.*prdNo=\d+', "11번가-gw"),
        (r'https?://link\.coupang\.com/re/.*pageKey=\d+', "쿠팡-aff"),
    ]

    # 우선순위 순으로 첫 번째 매칭
    for pattern, _ in PRIORITY_PATTERNS:
        for link in links:
            if re.search(pattern, str(link)):
                normalized = normalize_retailer_url(str(link))
                if normalized:
                    return normalized
    return None


def _parse_price(text: str) -> Optional[int]:
    digits = re.sub(r'[^\d]', '', text or '')
    if digits:
        val = int(digits)
        if 100 <= val <= 50_000_000:
            return val
    return None


def detect_retailer(url: str) -> str:
    if "gmarket.co.kr" in url:    return "gmarket"
    if "auction.co.kr" in url:    return "auction"
    if "11st.co.kr" in url:       return "11번가"
    if "lotteon.com" in url:      return "롯데온"
    if "coupang.com" in url:      return "쿠팡"
    if "smartstore.naver.com" in url: return "스마트스토어"
    if "ssg.com" in url:          return "SSG"
    return "unknown"


async def get_actual_price(url: str, playwright_page=None) -> Optional[PriceResult]:
    """
    실제 쇼핑몰 현재 가격 크롤링.
    playwright_page: 재사용 page 객체 (없으면 내부에서 브라우저 생성)
    """
    try:
        from playwright.async_api import async_playwright as _playwright
    except ImportError:
        logger.warning("[스크래퍼] playwright 미설치 — pip install playwright && playwright install chromium")
        return None

    retailer = detect_retailer(url)

    async def _scrape(page) -> Optional[PriceResult]:
        try:
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            await page.goto(url, timeout=12000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2500)

            content = await page.content()
            is_sold_out = any(t in content for t in SOLD_OUT_TEXTS)
            price = original = None

            # ── 지마켓 / 옥션 ──────────────────────────────
            if retailer in ("gmarket", "auction"):
                # .price_real 여러 개 → 가장 작은 값이 실제 판매가
                els = await page.query_selector_all(".price_real")
                prices = [_parse_price(await el.inner_text()) for el in els]
                prices = [p for p in prices if p]
                if prices:
                    price = min(prices)
                orig_el = await page.query_selector(".price_original, .text__price-original")
                if orig_el:
                    original = _parse_price(await orig_el.inner_text())

            # ── 11번가 ─────────────────────────────────────
            elif retailer == "11번가":
                for sel in [
                    ".price_block .price",   # 메인 판매가
                    ".price_info .price",
                    ".sel_price .price",
                    "em.text_num",
                ]:
                    el = await page.query_selector(sel)
                    if el:
                        p = _parse_price(await el.inner_text())
                        if p:
                            price = p
                            break

            # ── 롯데온 ─────────────────────────────────────
            elif retailer == "롯데온":
                for sel in ["strong.price", ".price_wrap strong", "[class*='salePrice'] strong"]:
                    el = await page.query_selector(sel)
                    if el:
                        p = _parse_price(await el.inner_text())
                        if p:
                            price = p
                            break
                orig_el = await page.query_selector(".price_origin, [class*='originPrice']")
                if orig_el:
                    original = _parse_price(await orig_el.inner_text())

            # ── 쿠팡 ───────────────────────────────────────
            elif retailer == "쿠팡":
                for sel in ["strong.total-price", ".prod-price strong", "[class*='totalPrice']"]:
                    el = await page.query_selector(sel)
                    if el:
                        p = _parse_price(await el.inner_text())
                        if p:
                            price = p
                            break

            # ── 네이버 스마트스토어 ─────────────────────────
            elif retailer == "스마트스토어":
                await page.wait_for_timeout(1500)  # SPA 로딩 대기
                for sel in [
                    "strong._2-I30U5RAP", "strong.price_num",
                    "[class*='price_num']", "strong._1LY7DqCnwR"
                ]:
                    el = await page.query_selector(sel)
                    if el:
                        p = _parse_price(await el.inner_text())
                        if p:
                            price = p
                            break

            # ── SSG ────────────────────────────────────────
            elif retailer == "SSG":
                for sel in ["strong.ssg_price", ".cunit_price strong", "em.ssg_price"]:
                    el = await page.query_selector(sel)
                    if el:
                        p = _parse_price(await el.inner_text())
                        if p:
                            price = p
                            break

            if price is None:
                logger.debug(f"[스크래퍼] 가격 미발견: {retailer} {url[:50]}")
                return None

            return PriceResult(
                price=price,
                original_price=original or price,
                in_stock=not is_sold_out,
                retailer=retailer,
                url=page.url,
            )
        except Exception as e:
            logger.debug(f"[스크래퍼] {retailer} 오류: {e}")
            return None

    if playwright_page:
        return await _scrape(playwright_page)

    try:
        async with _playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
                      "--disable-blink-features=AutomationControlled"],
            )
            ctx = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                ),
                locale="ko-KR",
                viewport={"width": 1280, "height": 800},
            )
            page = await ctx.new_page()
            result = await _scrape(page)
            await browser.close()
            return result
    except Exception as e:
        logger.debug(f"[스크래퍼] 브라우저 오류: {e}")
        return None


async def fetch_retailer_url_from_ppomppu(ppomppu_post_url: str, playwright_page=None) -> Optional[str]:
    """
    뽐뿌 포스트 URL → 실제 쇼핑몰 URL 추출
    Playwright로 페이지 렌더링 후 모든 링크 추출 → 쇼핑몰 URL 파싱
    """
    try:
        from playwright.async_api import async_playwright as _playwright
    except ImportError:
        return None

    async def _extract(page) -> Optional[str]:
        try:
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            await page.goto(ppomppu_post_url, timeout=12000, wait_until="domcontentloaded")
            await page.wait_for_timeout(1000)

            links = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a[href]')).map(a => a.href);
            }""")
            return extract_retailer_links_from_page(links)
        except Exception as e:
            logger.debug(f"[ppomppu URL 추출] 오류: {e}")
            return None

    if playwright_page:
        return await _extract(playwright_page)

    try:
        async with _playwright() as pw:
            browser = await pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            ctx = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
                locale="ko-KR",
            )
            page = await ctx.new_page()
            result = await _extract(page)
            await browser.close()
            return result
    except Exception as e:
        logger.debug(f"[ppomppu URL 추출] 브라우저 오류: {e}")
        return None
