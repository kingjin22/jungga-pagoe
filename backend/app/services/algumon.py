"""
알구몬 API 기반 커뮤니티 딜 수집기
https://www.algumon.com/api/posts

대상 채널: 뽐뿌, 루리웹, 어미새, 아카라이브
- 식품/일상용품 자동 차단
- Naver MSRP 자동 탐지로 정가 계산
- 해외 딜(알리, 아마존, 스팀 등) 차단
"""
import re
import asyncio
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

ALGUMON_API = "https://www.algumon.com/api/posts"

# 수집 대상 사이트명 (알구몬 siteName 값)
TARGET_SITES = {"뽐뿌", "루리웹", "어미새", "아카라이브", "클리앙", "퀘이사존"}

# 해외 쇼핑몰 차단 (storeName 기준)
OVERSEAS_STORES = {
    "알리", "알리익스프레스", "아마존", "amazon", "aliexpress",
    "ebay", "이베이", "스팀", "steam", "epic", "에픽",
    "nintendo", "닌텐도", "playstation", "플스",
    "라쿠텐", "qoo10", "큐텐", "에픽게임즈", "에픽모바일",
    "에셋스토어", "bandai", "반다이몰", "그린맨게이밍",
    "스위치", "ps5", "xbox", "겜우리",
}

# 루리웹 카테고리 차단 목록 (해외/상품권 제외)
RULIWEB_BLOCKED_CATEGORIES = {"음식", "상품권", "무료", "알리"}


def _parse_price(text: str) -> Optional[int]:
    """'37,710원' → 37710"""
    if not text:
        return None
    nums = re.sub(r"[^\d]", "", text)
    return int(nums) if nums else None


def _is_overseas(title: str, store_name: str) -> bool:
    """해외딜 감지"""
    store_l = (store_name or "").lower()
    title_l = title.lower()
    if any(s in store_l for s in OVERSEAS_STORES):
        return True
    # 제목 내 영어 비율이 50% 이상이면 해외딜 가능성
    alpha = sum(1 for c in title if c.isascii() and c.isalpha())
    if alpha > len(title) * 0.5:
        return True
    return False


async def fetch_algumon_deals(pages: int = 5) -> list[dict]:
    """
    알구몬 API 다중 페이지 수집 (10개 × pages)
    pagination: minId 기반
    """
    all_posts = []
    max_id = None

    async with httpx.AsyncClient(
        timeout=10,
        headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
    ) as client:
        for i in range(pages):
            try:
                params = {}
                if max_id:
                    params["maxId"] = max_id - 1
                r = await client.get(ALGUMON_API, params=params)
                data = r.json()
                page_data = data.get("data", {})
                posts = page_data.get("posts", [])
                if not posts:
                    break
                all_posts.extend(posts)
                max_id = page_data.get("minId")
                if not max_id or page_data.get("noMorePost"):
                    break
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.warning(f"[알구몬] 페이지{i+1} 수집 실패: {e}")
                break

    logger.debug(f"[알구몬] 총 {len(all_posts)}개 수집")
    return all_posts


async def fetch_ruliweb_deals() -> list[dict]:
    """
    루리웹 RSS 직접 파싱 (게임H/W, 전자기기 카테고리 특화)
    """
    import xml.etree.ElementTree as ET

    RULIWEB_RSS = "https://bbs.ruliweb.com/market/board/1020/rss"
    # 루리웹 차단 카테고리
    BLOCKED_CATS = {"음식", "상품권", "무료나눔", "알리"}

    try:
        async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0"}) as client:
            r = await client.get(RULIWEB_RSS)
            root = ET.fromstring(r.text)
    except Exception as e:
        logger.warning(f"[루리웹RSS] 수집 실패: {e}")
        return []

    posts = []
    for item in root.findall(".//item"):
        title_el = item.find("title")
        link_el = item.find("link")
        cat_el = item.find("category")
        desc_el = item.find("description")

        title = (title_el.text or "").strip() if title_el is not None else ""
        link = (link_el.text or "").strip() if link_el is not None else ""
        cat = (cat_el.text or "").strip() if cat_el is not None else ""
        desc_html = desc_el.text if desc_el is not None else ""

        if cat in BLOCKED_CATS:
            continue
        if not title or not link:
            continue

        # 이미지 추출
        img = ""
        if desc_html:
            m = re.search(r'src="([^"]+)"', desc_html or "")
            if m:
                img = m.group(1)

        # 가격 추출 (제목에서) - 괄호 있거나 없거나 모두 처리
        price_m = re.search(r"[\₩￦]?([\d,]+)원", title)
        price = int(price_m.group(1).replace(",", "")) if price_m else 0

        # 제목 정리: 가격 부분 + 쇼핑몰 태그([스팀] 등) 제거
        import html as html_module
        clean_title = html_module.unescape(title)  # &amp; 등 HTML 엔티티 디코딩
        clean_title = re.sub(r"^\[[^\]]+\]\s*", "", clean_title)  # 앞 쇼핑몰 태그 제거
        clean_title = re.sub(r"\s+[\₩￦]?[\d,]+원.*$", "", clean_title).strip()  # 뒷 가격 제거

        # storeName: 쇼핑몰 태그 추출
        mall_m = re.match(r"^\[([^\]]+)\]", title)
        store = mall_m.group(1) if mall_m else ""

        posts.append({
            "deal": {
                "siteName": "루리웹",
                "storeName": store,
                "title": clean_title or title,
                "linkUrl": link,
                "thumbnailUrl": img,
                "priceText": f"{price:,}원" if price else "",
                "siteLikes": 0,
                "siteComments": 0,
                "category": cat,
            }
        })

    logger.debug(f"[루리웹RSS] {len(posts)}개 수집")
    return posts


async def process_algumon_deals(
    raw_posts: list[dict],
    existing_urls: set[str],
) -> list[dict]:
    """
    알구몬 딜 전처리:
    1. 대상 사이트 필터
    2. 해외딜 차단
    3. 식품/일상용품 차단
    4. Naver MSRP 탐지
    5. 할인율 계산
    """
    from app.services.community_enricher import is_food_or_daily

    results = []
    seen_urls = set(existing_urls)

    for post in raw_posts:
        deal = post.get("deal", {})
        if not deal:
            continue

        site_name = deal.get("siteName", "")
        store_name = deal.get("storeName", "") or ""
        title = (deal.get("title") or "").strip()
        price_text = deal.get("priceText", "") or ""
        link_url = (deal.get("linkUrl") or "").strip()
        thumbnail = deal.get("thumbnailUrl") or ""
        likes = deal.get("siteLikes", 0) or 0

        # ① 대상 사이트 필터
        if site_name not in TARGET_SITES:
            continue

        # ② URL 중복 체크
        if not link_url or link_url in seen_urls:
            continue

        # ③ 해외딜 차단
        if _is_overseas(title, store_name):
            continue

        # ④ 식품/일상용품 차단
        if is_food_or_daily(title):
            continue

        # ⑤ 가격 파싱
        sale_price = _parse_price(price_text)
        if not sale_price or sale_price < 1000:
            continue

        seen_urls.add(link_url)

        # 커뮤니티 딜: MSRP 없이 판매가만 노출 (원글 만료 시 자동 만료)
        results.append({
            "title": title,
            "sale_price": sale_price,
            "original_price": 0,   # 정가 미확인 — 커뮤니티 딜
            "discount_rate": 0,
            "product_url": link_url,
            "source_post_url": link_url,
            "image_url": thumbnail,
            "source": "community",
            "category": "기타",
            "description": f"출처: {site_name} | {store_name}",
            "submitter_name": site_name,
            "algumon_likes": likes,
        })

        await asyncio.sleep(0.1)  # Naver API 요청 간격

    return results
