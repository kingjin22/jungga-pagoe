"""
이미지 및 실제 상품 URL 추출기
뽐뿌: CDN 이미지(cdn2.ppomppu.co.kr/data3) + JS 내 쇼핑몰 URL 추출
일반: og:image 메타태그
"""
import httpx
import re
from bs4 import BeautifulSoup
from typing import Optional

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

NON_SHOPPING = (
    # 뽐뿌 자체
    "ppomppu.co.kr", "cdn2.ppomppu",
    # 광고/트래킹
    "doubleclick.net", "googlesyndication", "googletagmanager",
    "google-analytics", "adservice", "googleadservices",
    "analytics.", "tracking.", "pixel.",
    # 표준/메타
    "w3.org", "schema.org", "xml.org", "xmlns", "apple.com/dtd",
    # SNS
    "google.", "facebook.", "twitter.", "instagram.", "youtube.",
    "kakao.com/link", "kakaocorp.com",
    # 단축URL (최종 목적지 아님)
    "t.co/", "bit.ly", "goo.gl", "tinyurl",
    # JS/CSS
    ".js", ".css",
)


def _is_shopping_url(url: str) -> bool:
    """실제 쇼핑몰 상품 URL인지 판별 (광고/트래킹/SNS 제외)"""
    if any(x in url for x in NON_SHOPPING):
        return False
    from urllib.parse import urlparse
    try:
        p = urlparse(url)
        return bool(p.netloc and "." in p.netloc and (p.path.strip("/") or p.query))
    except Exception:
        return False


async def get_og_image(url: str, timeout: float = 6.0) -> Optional[str]:
    """URL에서 og:image 추출"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=HEADERS, timeout=timeout, follow_redirects=True)
            if resp.status_code >= 400:
                return None
            html = resp.text[:20000]
            soup = BeautifulSoup(html, "html.parser")

            for attr in [{"property": "og:image"}, {"name": "og:image"}, {"name": "twitter:image"}]:
                tag = soup.find("meta", attrs=attr)
                if tag and tag.get("content", "").startswith("http"):
                    return tag["content"].strip()
    except Exception:
        pass
    return None


async def extract_product_from_ppomppu(ppomppu_url: str) -> dict:
    """
    뽐뿌 게시글 파싱:
    - 이미지: cdn2.ppomppu.co.kr/zboard/data3/ 경로 (본문 업로드 이미지)
    - 상품URL: HTML/JS 내 쇼핑몰 도메인 URL
    """
    result = {"product_url": ppomppu_url, "image_url": None}

    # http → https 변환 (뽐뿌는 리다이렉트함)
    url = ppomppu_url.replace("http://", "https://")

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=HEADERS, timeout=10.0, follow_redirects=True)
            if resp.status_code >= 400:
                return result

            html = resp.text

            # 1. 본문 업로드 이미지 추출 (data3 경로 = 사용자가 올린 상품 이미지)
            img_match = re.search(
                r'(https?:)?//cdn2\.ppomppu\.co\.kr/zboard/data3/[^\s"\'<>]+\.(jpg|jpeg|png|gif|webp)',
                html, re.IGNORECASE
            )
            if img_match:
                img_url = img_match.group(0)
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                result["image_url"] = img_url

            # 2. 실제 상품 URL 추출
            # 방법 A: data-url 속성 (뽐뿌가 광고 트래킹용으로 사용)
            soup_page = BeautifulSoup(html, "html.parser")
            for tag in soup_page.find_all(True, attrs={"data-url": True}):
                du = tag.get("data-url", "")
                if du.startswith("http") and _is_shopping_url(du):
                    result["product_url"] = du
                    break

            # 방법 B: s.ppomppu.co.kr?target=base64 디코딩
            if result["product_url"] == url:
                import base64
                from urllib.parse import urlparse, parse_qs
                for a in soup_page.find_all("a", href=True):
                    href = a["href"]
                    if "s.ppomppu.co.kr" in href and "target=" in href:
                        try:
                            qs = parse_qs(urlparse(href).query)
                            encoded = qs.get("target", [""])[0]
                            # base64 패딩 보정
                            padding = 4 - len(encoded) % 4
                            decoded = base64.b64decode(encoded + "=" * padding).decode("utf-8")
                            if decoded.startswith("http") and _is_shopping_url(decoded):
                                result["product_url"] = decoded
                                break
                        except Exception:
                            pass

    except Exception as e:
        pass

    # 이미지 못 찾았으면 실제 상품 URL의 og:image 시도
    if not result["image_url"] and result["product_url"] != ppomppu_url:
        result["image_url"] = await get_og_image(result["product_url"], timeout=5.0)

    return result


async def enrich_deal_with_image(deal: dict) -> dict:
    """딜 dict에 image_url과 실제 product_url 채우기"""
    product_url = deal.get("product_url", "")

    if "ppomppu.co.kr" in product_url:
        info = await extract_product_from_ppomppu(product_url)
        deal["product_url"] = info["product_url"]
        if info["image_url"]:
            deal["image_url"] = info["image_url"]
    elif not deal.get("image_url"):
        deal["image_url"] = await get_og_image(product_url)

    return deal
