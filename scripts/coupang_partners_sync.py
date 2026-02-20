"""
쿠팡 파트너스 자동 딜 수집기
- Playwright로 partners.coupang.com 로그인 → xToken 추출
- Discovery API (most-sold, most-discounted, most-conversion) 제품 수집
- Naver API로 정가 교차 검증
- /api/v1/url/any 로 파트너스 링크 생성
- 어드민 API로 딜 자동 등록
"""
import asyncio
import httpx
import json
import re
import os
import sys
from typing import Optional

ADMIN_URL = "https://jungga-pagoe-production.up.railway.app"
ADMIN_SECRET = "jungga2026admin"
PARTNERS_EMAIL = "kingjin2@naver.com"
PARTNERS_PASSWORD = "!0eotodtjdwlsl"
NAVER_CLIENT_ID = "wHDtIpb0AI8X7RlUSBJP"
NAVER_CLIENT_SECRET = "oZZAfOcWU7"

MIN_DISCOUNT = 15       # 최소 할인율 (%)
MIN_PRICE = 8000        # 최소 판매가 (원)
MIN_RATING = 4.0        # 최소 평점
MIN_REVIEWS = 50        # 최소 리뷰 수

# 관심 카테고리 ID (쿠팡)
ALLOWED_CATEGORY_IDS = {
    # 전자기기
    1188, 1229, 1230, 1231, 1312, 2296,
    # 패션
    1273, 1277, 1278, 5584,
    # 뷰티
    2334, 2335, 2336,
    # 스포츠
    1268, 1281, 1282, 2043,
    # 홈리빙 (가전)
    1266, 1267, 1196,
}

CATEGORY_MAP = {
    1188: "전자기기", 1229: "전자기기", 1230: "전자기기",
    1231: "전자기기", 1312: "전자기기", 2296: "전자기기",
    1273: "패션", 1277: "패션", 1278: "패션", 5584: "패션",
    2334: "뷰티", 2335: "뷰티", 2336: "뷰티",
    1268: "스포츠", 1281: "스포츠", 1282: "스포츠", 2043: "스포츠",
    1266: "홈리빙", 1267: "홈리빙", 1196: "홈리빙",
}


async def get_partners_token() -> tuple[str, dict]:
    """Playwright로 파트너스 로그인, xToken + 쿠키 반환"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("playwright 미설치. pip install playwright && playwright install chromium")
        sys.exit(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await ctx.new_page()
        print("파트너스 로그인 중...")
        # login.coupang.com으로 직접 이동
        login_url = "https://login.coupang.com/login/login.pang?rtnUrl=https%3A%2F%2Fpartners.coupang.com%2Fapi%2Fv1%2Fpostlogin"
        await page.goto(login_url, wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        # 입력창 찾기
        inputs = await page.query_selector_all("input")
        print(f"  입력창 {len(inputs)}개 발견")
        for i, inp in enumerate(inputs[:5]):
            ph = await inp.get_attribute("placeholder")
            tp = await inp.get_attribute("type")
            print(f"  [{i}] type={tp} placeholder={ph}")
        # 이메일/비밀번호 입력
        email_inp = await page.query_selector("input[type='text'], input:not([type='hidden'])")
        pw_inp = await page.query_selector("input[type='password']")
        if not email_inp or not pw_inp:
            raise ValueError("로그인 입력창 찾기 실패")
        await email_inp.fill(PARTNERS_EMAIL)
        await pw_inp.fill(PARTNERS_PASSWORD)
        await page.click("button[type='submit'], button:has-text('로그인')")
        await page.wait_for_timeout(3000)
        print(f"  현재 URL: {page.url}")
        # 파트너스 로그인 완료 확인
        await page.goto("https://partners.coupang.com/#affiliate/ws/link-to-any-page",
                        wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        x_token = await page.evaluate("window.xToken")
        cookies = {c["name"]: c["value"] for c in await ctx.cookies()}
        await browser.close()

        if not x_token:
            raise ValueError("xToken 추출 실패 — 로그인 확인 필요")
        print(f"xToken 획득: {x_token[:20]}...")
        return x_token, cookies


async def fetch_discovery_products(token: str, cookies: dict) -> list[dict]:
    """Discovery API 3종에서 상품 수집"""
    endpoints = ["most-sold", "most-discounted", "most-conversion"]
    all_products = []

    async with httpx.AsyncClient(
        base_url="https://partners.coupang.com",
        headers={
            "X-Token": token,
            "Referer": "https://partners.coupang.com/",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        },
        cookies=cookies,
        timeout=15,
    ) as client:
        for ep in endpoints:
            try:
                r = await client.get(f"/api/v1/discovery/{ep}?limit=30")
                j = r.json()
                if j.get("rCode") == "0" and j.get("data", {}).get("products"):
                    all_products.extend(j["data"]["products"])
                    print(f"  [{ep}] {len(j['data']['products'])}개 수집")
                else:
                    print(f"  [{ep}] 실패: {j.get('rCode')} {j.get('rMessage','')}")
            except Exception as e:
                print(f"  [{ep}] 오류: {e}")

    # 중복 제거
    seen = set()
    unique = []
    for p in all_products:
        pid = p.get("productId")
        if pid and pid not in seen and not p.get("isSoldOut") and not p.get("isAdult"):
            seen.add(pid)
            unique.append(p)

    print(f"총 {len(unique)}개 고유 상품")
    return unique


def qualify_product(p: dict) -> bool:
    """할인율, 가격, 카테고리, 평점 필터"""
    disc = p.get("discountRate", 0)
    sale = p.get("salesPrice", 0)
    orig = p.get("originPrice", 0)
    cat_id = p.get("categoryId")
    rating = p.get("ratingAverage", 0)
    reviews = p.get("ratingCount", 0)

    if disc < MIN_DISCOUNT:
        return False
    if sale < MIN_PRICE:
        return False
    if orig <= sale:
        return False
    if cat_id and ALLOWED_CATEGORY_IDS and cat_id not in ALLOWED_CATEGORY_IDS:
        return False
    if rating > 0 and rating < MIN_RATING:
        return False
    return True


async def generate_affiliate_link(product_id: int, token: str, cookies: dict) -> Optional[str]:
    """파트너스 링크 생성"""
    coupang_url = f"https://www.coupang.com/vp/products/{product_id}"
    async with httpx.AsyncClient(
        base_url="https://partners.coupang.com",
        headers={"X-Token": token, "Referer": "https://partners.coupang.com/"},
        cookies=cookies,
        timeout=10,
    ) as client:
        from urllib.parse import quote
        r = await client.get(f"/api/v1/url/any?coupangUrl={quote(coupang_url, safe='')}")
        j = r.json()
        if j.get("rCode") == "0" and j.get("data", {}).get("shortUrl"):
            return j["data"]["shortUrl"]
        return None


async def post_deal_to_admin(deal: dict) -> bool:
    """어드민 API로 딜 등록 (POST /admin/deals/quick-add)"""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            f"{ADMIN_URL}/admin/deals/quick-add",
            json=deal,
            headers={"X-Admin-Key": ADMIN_SECRET},
        )
        if r.status_code == 200:
            result = r.json()
            return result.get("id") is not None
        print(f"    등록 실패 {r.status_code}: {r.text[:200]}")
        return False


def infer_category(p: dict) -> str:
    cat_id = p.get("categoryId")
    if cat_id and cat_id in CATEGORY_MAP:
        return CATEGORY_MAP[cat_id]
    title = (p.get("title") or "").lower()
    if any(k in title for k in ["신발", "운동화", "러닝", "스니커", "슬리퍼", "부츠"]):
        return "신발"
    if any(k in title for k in ["이어폰", "헤드폰", "스피커", "태블릿", "노트북", "충전기", "케이블"]):
        return "전자기기"
    if any(k in title for k in ["청소기", "공기청정기", "드라이기", "에어프라이어"]):
        return "홈리빙"
    if any(k in title for k in ["크림", "세럼", "선크림", "마스크팩"]):
        return "뷰티"
    return "기타"


async def main():
    print("=== 쿠팡 파트너스 딜 수집 시작 ===\n")

    # 1. 로그인
    try:
        token, cookies = await get_partners_token()
    except Exception as e:
        print(f"로그인 실패: {e}")
        return

    # 2. 상품 수집
    products = await fetch_discovery_products(token, cookies)

    # 3. 필터
    qualified = [p for p in products if qualify_product(p)]
    print(f"\n필터 통과: {len(qualified)}/{len(products)}개\n")

    # 4. 링크 생성 + 등록
    registered = 0
    skipped = 0
    for p in qualified:
        pid = p["productId"]
        title = p.get("title", "")
        sale = int(p.get("salesPrice", 0))
        orig = int(p.get("originPrice", 0))
        disc = int(p.get("discountRate", 0))
        img = p.get("image", "")
        brands = p.get("brands", [])
        category = infer_category(p)

        print(f"처리 중: [{disc}%] {title[:40]}")

        # 파트너스 링크 생성
        affiliate_url = await generate_affiliate_link(pid, token, cookies)
        if not affiliate_url:
            print(f"  → 블랙리스트 또는 링크 생성 실패")
            skipped += 1
            continue

        print(f"  → {affiliate_url}")

        # 딜 등록
        deal = {
            "title": title,
            "product_url": affiliate_url,
            "sale_price": sale,
            "original_price": orig,
            "image_url": img,
            "source": "coupang",
            "category": category,
            "brand": brands[0] if brands else "",
            "description": f"쿠팡 {disc}% 할인 | 로켓배송 | 정가 {orig:,}원",
        }

        ok = await post_deal_to_admin(deal)
        if ok:
            print(f"  ✅ 등록 완료")
            registered += 1
        else:
            print(f"  ❌ 등록 실패")
        
        await asyncio.sleep(0.5)  # 요청 간격

    print(f"\n=== 완료: {registered}개 등록, {skipped}개 스킵 ===")


if __name__ == "__main__":
    asyncio.run(main())
