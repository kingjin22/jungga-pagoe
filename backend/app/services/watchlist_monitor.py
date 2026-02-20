"""
watchlist_monitor.py — 인기 제품 가격 추적 & 자동 딜 등록

파이프라인:
1. product_watchlist 테이블에서 활성 제품 로드
2. Naver Shopping API로 현재 lprice 조회
3. 30일 평균 대비 alert_threshold% 이상 하락 시 딜 자동 등록
4. 주 1회 KREAM 트렌딩 → 워치리스트 자동 갱신
"""
import asyncio
import logging
import re
import httpx
from datetime import datetime, timezone, timedelta
from app.config import settings

logger = logging.getLogger(__name__)

NAVER_API_BASE = "https://openapi.naver.com/v1"

# ─────────────────────────────────────────────────────────────
# 초기 워치리스트 (수동 등록 — KREAM 갱신 전 기본값)
# ─────────────────────────────────────────────────────────────
INITIAL_WATCHLIST = [
    # ── 러닝화 ────────────────────────────────────────────────
    # Nike
    {"name": "나이키 페가수스 41", "search_query": "나이키 페가수스 41 런닝화", "category": "신발", "brand": "Nike", "msrp": 159000, "min_price": 60000},
    {"name": "나이키 인빈시블 런 3", "search_query": "나이키 인빈시블 런 3", "category": "신발", "brand": "Nike", "msrp": 239000, "min_price": 100000},
    {"name": "나이키 보메로 18", "search_query": "나이키 보메로 18 런닝화", "category": "신발", "brand": "Nike", "msrp": 199000, "min_price": 80000},
    {"name": "나이키 줌플라이 6", "search_query": "나이키 줌플라이 6", "category": "신발", "brand": "Nike", "msrp": 249000, "min_price": 100000},
    {"name": "나이키 에어 줌 알파플라이 3", "search_query": "나이키 알파플라이 3", "category": "신발", "brand": "Nike", "msrp": 369000, "min_price": 150000},
    # Adidas
    {"name": "아디다스 아디제로 보스턴 12", "search_query": "아디다스 아디제로 보스턴 12", "category": "신발", "brand": "Adidas", "msrp": 189000, "min_price": 80000},
    {"name": "아디다스 아디제로 아디오스 프로 3", "search_query": "아디다스 아디오스 프로 3", "category": "신발", "brand": "Adidas", "msrp": 369000, "min_price": 150000},
    {"name": "아디다스 울트라부스트 22", "search_query": "아디다스 울트라부스트 22 런닝화", "category": "신발", "brand": "Adidas", "msrp": 229000, "min_price": 90000},
    # Asics
    {"name": "아식스 젤 카야노 31", "search_query": "아식스 젤카야노 31", "category": "신발", "brand": "Asics", "msrp": 209000, "min_price": 80000},
    {"name": "아식스 겔 님버스 26", "search_query": "아식스 겔 님버스 26", "category": "신발", "brand": "Asics", "msrp": 229000, "min_price": 90000},
    {"name": "아식스 슈퍼블라스트 2", "search_query": "아식스 슈퍼블라스트 2", "category": "신발", "brand": "Asics", "msrp": 269000, "min_price": 110000},
    {"name": "아식스 메타스피드 스카이+", "search_query": "아식스 메타스피드 스카이", "category": "신발", "brand": "Asics", "msrp": 399000, "min_price": 160000},
    {"name": "아식스 젤 쿠무루스 26", "search_query": "아식스 젤쿠무루스 26", "category": "신발", "brand": "Asics", "msrp": 149000, "min_price": 60000},
    # Saucony
    {"name": "써코니 엔돌핀 스피드 4", "search_query": "써코니 엔돌핀 스피드 4", "category": "신발", "brand": "Saucony", "msrp": 219000, "min_price": 90000},
    {"name": "써코니 킨바라 15", "search_query": "써코니 킨바라 15", "category": "신발", "brand": "Saucony", "msrp": 149000, "min_price": 60000},
    {"name": "써코니 트라이엄프 22", "search_query": "써코니 트라이엄프 22", "category": "신발", "brand": "Saucony", "msrp": 199000, "min_price": 80000},
    {"name": "써코니 엔돌핀 프로 4", "search_query": "써코니 엔돌핀 프로 4", "category": "신발", "brand": "Saucony", "msrp": 319000, "min_price": 130000},
    # Brooks
    {"name": "브룩스 고스트 16", "search_query": "브룩스 고스트 16 런닝화", "category": "신발", "brand": "Brooks", "msrp": 179000, "min_price": 70000},
    {"name": "브룩스 글리세린 22", "search_query": "브룩스 글리세린 22", "category": "신발", "brand": "Brooks", "msrp": 219000, "min_price": 90000},
    {"name": "브룩스 하이페리온 맥스 2", "search_query": "브룩스 하이페리온 맥스 2", "category": "신발", "brand": "Brooks", "msrp": 269000, "min_price": 110000},
    {"name": "브룩스 아드레날린 GTS 24", "search_query": "브룩스 아드레날린 GTS 24", "category": "신발", "brand": "Brooks", "msrp": 189000, "min_price": 80000},
    # HOKA
    {"name": "호카 클리프턴 9", "search_query": "호카 클리프턴 9 런닝화", "category": "신발", "brand": "HOKA", "msrp": 179000, "min_price": 70000},
    {"name": "호카 본다이 8", "search_query": "호카 본다이 8", "category": "신발", "brand": "HOKA", "msrp": 219000, "min_price": 90000},
    {"name": "호카 마하 6", "search_query": "호카 마하 6", "category": "신발", "brand": "HOKA", "msrp": 219000, "min_price": 90000},
    {"name": "호카 로켓 X2", "search_query": "호카 로켓 X2", "category": "신발", "brand": "HOKA", "msrp": 349000, "min_price": 140000},
    # New Balance
    {"name": "뉴발란스 1080 v14", "search_query": "뉴발란스 1080 v14 런닝화", "category": "신발", "brand": "New Balance", "msrp": 219000, "min_price": 90000},
    {"name": "뉴발란스 SC 엘리트 v4", "search_query": "뉴발란스 SC엘리트 v4", "category": "신발", "brand": "New Balance", "msrp": 329000, "min_price": 140000},
    # On Running
    {"name": "온러닝 클라우드몬스터 2", "search_query": "온러닝 클라우드몬스터 2", "category": "신발", "brand": "On Running", "msrp": 239000, "min_price": 100000},
    {"name": "온러닝 클라우드서퍼 7", "search_query": "온러닝 클라우드서퍼 7", "category": "신발", "brand": "On Running", "msrp": 199000, "min_price": 80000},

    # ── 스니커즈 ──────────────────────────────────────────────
    {"name": "나이키 에어포스 1 '07", "search_query": "나이키 에어포스1 07", "category": "신발", "brand": "Nike", "msrp": 129000, "min_price": 60000},
    {"name": "나이키 에어맥스 97", "search_query": "나이키 에어맥스 97", "category": "신발", "brand": "Nike", "msrp": 199000, "min_price": 80000},
    {"name": "나이키 덩크 로우", "search_query": "나이키 덩크로우", "category": "신발", "brand": "Nike", "msrp": 139000, "min_price": 60000},
    {"name": "아디다스 삼바 OG", "search_query": "아디다스 삼바 OG", "category": "신발", "brand": "Adidas", "msrp": 139000, "min_price": 60000},
    {"name": "뉴발란스 1906R", "search_query": "뉴발란스 1906R 스니커즈", "category": "신발", "brand": "New Balance", "msrp": 179000, "min_price": 70000},
    {"name": "뉴발란스 530", "search_query": "뉴발란스 530 스니커즈", "category": "신발", "brand": "New Balance", "msrp": 109000, "min_price": 45000},

    # ── 전자기기 ──────────────────────────────────────────────
    {"name": "에어팟 프로 2세대 USB-C", "search_query": "애플 에어팟 프로 2세대 USB-C", "category": "전자기기", "brand": "Apple", "msrp": 359000, "min_price": 200000},
    {"name": "에어팟 4 ANC", "search_query": "애플 에어팟 4 ANC", "category": "전자기기", "brand": "Apple", "msrp": 279000, "min_price": 150000},
    {"name": "소니 WH-1000XM5", "search_query": "소니 WH-1000XM5 헤드폰", "category": "전자기기", "brand": "Sony", "msrp": 449000, "min_price": 200000},
    {"name": "소니 WF-1000XM5", "search_query": "소니 WF-1000XM5 이어폰", "category": "전자기기", "brand": "Sony", "msrp": 359000, "min_price": 160000},
    {"name": "갤럭시 버즈3 프로", "search_query": "삼성 갤럭시버즈3 프로", "category": "전자기기", "brand": "Samsung", "msrp": 329000, "min_price": 150000},
    {"name": "갤럭시 워치7 44mm", "search_query": "삼성 갤럭시워치7 44mm", "category": "전자기기", "brand": "Samsung", "msrp": 329000, "min_price": 150000},
    {"name": "애플워치 SE 2세대 44mm", "search_query": "애플워치 SE 2세대 44mm", "category": "전자기기", "brand": "Apple", "msrp": 349000, "min_price": 180000},
    {"name": "앤커 파워코어 슬림 10000 PD", "search_query": "앤커 파워코어 슬림 10000 PD", "category": "전자기기", "brand": "Anker", "msrp": 49000, "min_price": 20000},
    {"name": "아이패드 미니 7세대", "search_query": "애플 아이패드 미니 7세대 2024", "category": "전자기기", "brand": "Apple", "msrp": 799000, "min_price": 500000},

    # ── 생활가전 ──────────────────────────────────────────────
    {"name": "다이슨 V15 디텍트", "search_query": "다이슨 V15 디텍트 청소기", "category": "생활가전", "brand": "Dyson", "msrp": 1099000, "min_price": 600000},
    {"name": "다이슨 에어랩 컴플리트 롱", "search_query": "다이슨 에어랩 컴플리트 롱", "category": "생활가전", "brand": "Dyson", "msrp": 999000, "min_price": 500000},
    {"name": "다이슨 슈퍼소닉", "search_query": "다이슨 슈퍼소닉 드라이어", "category": "생활가전", "brand": "Dyson", "msrp": 649000, "min_price": 350000},
    {"name": "LG 코드제로 A9S", "search_query": "LG 코드제로 A9S 청소기", "category": "생활가전", "brand": "LG", "msrp": 849000, "min_price": 450000},
    {"name": "드롱기 디디카 에스프레소", "search_query": "드롱기 디디카 에스프레소 머신", "category": "생활가전", "brand": "De'Longhi", "msrp": 399000, "min_price": 200000},

    # ── 뷰티 ─────────────────────────────────────────────────
    {"name": "설화수 자음생 크림 75ml", "search_query": "설화수 자음생 크림 75ml", "category": "뷰티", "brand": "Sulwhasoo", "msrp": 135000, "min_price": 70000},
    {"name": "에스티로더 어드밴스드 나이트 리페어", "search_query": "에스티로더 어드밴스드 나이트 리페어 세럼", "category": "뷰티", "brand": "Estee Lauder", "msrp": 159000, "min_price": 80000},
    {"name": "SK-II 피테라 에센스 230ml", "search_query": "SKII 피테라 에센스 230ml", "category": "뷰티", "brand": "SK-II", "msrp": 299000, "min_price": 150000},

    # ── 아웃도어/패션 ─────────────────────────────────────────
    {"name": "노스페이스 눕시 패딩 2024", "search_query": "노스페이스 눕시 패딩 2024", "category": "패션", "brand": "The North Face", "msrp": 359000, "min_price": 150000},
    {"name": "아크테릭스 아톰 LT 후디", "search_query": "아크테릭스 아톰 LT 후디", "category": "패션", "brand": "Arc'teryx", "msrp": 569000, "min_price": 280000},
    {"name": "파타고니아 다운 스웨터", "search_query": "파타고니아 다운 스웨터", "category": "패션", "brand": "Patagonia", "msrp": 369000, "min_price": 150000},
]


# ─────────────────────────────────────────────────────────────
# Naver 가격 조회
# ─────────────────────────────────────────────────────────────
def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


async def _naver_lprice(query: str, client: httpx.AsyncClient) -> tuple[int, int, str | None]:
    """(lprice, hprice, image_url) — 실패 시 (0, 0, None)"""
    if not settings.NAVER_CLIENT_ID:
        return 0, 0, None
    try:
        resp = await client.get(
            f"{NAVER_API_BASE}/search/shop.json",
            headers={
                "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
                "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
            },
            params={"query": query, "display": 10, "sort": "sim"},
            timeout=8,
        )
        items = resp.json().get("items", [])
        prices = [(int(i.get("lprice", 0)), int(i.get("hprice", 0)), i.get("image")) for i in items if i.get("lprice")]
        if not prices:
            return 0, 0, None
        # 최저가 기준 정렬
        prices.sort(key=lambda x: x[0])
        return prices[0][0], prices[0][1], prices[0][2]
    except Exception as e:
        logger.debug(f"[워치리스트] Naver 조회 실패 ({query}): {e}")
        return 0, 0, None


# ─────────────────────────────────────────────────────────────
# KREAM 트렌딩 스크래퍼
# ─────────────────────────────────────────────────────────────
async def scrape_kream_trending(client: httpx.AsyncClient) -> list[dict]:
    """KREAM 인기 제품 상위 50개 추출 → 워치리스트에 없는 제품 반환"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://kream.co.kr/",
        }
        # KREAM API (앱 트래픽 기반)
        resp = await client.get(
            "https://kream.co.kr/api/products/popular",
            headers=headers,
            params={"page": 1, "size": 50, "category_id": ""},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.info(f"[KREAM] API 응답 {resp.status_code} — 대체 파싱 시도")
            return await _scrape_kream_html(client)

        data = resp.json()
        products = []
        for item in data.get("products", []):
            name = item.get("name") or item.get("translated_name", "")
            brand = item.get("brand", {}).get("name", "")
            if not name:
                continue
            products.append({"name": name, "brand": brand, "source": "kream"})
        logger.info(f"[KREAM] {len(products)}개 트렌딩 제품 수집")
        return products
    except Exception as e:
        logger.warning(f"[KREAM] 스크래핑 실패: {e}")
        return []


async def _scrape_kream_html(client: httpx.AsyncClient) -> list[dict]:
    """KREAM HTML 파싱 fallback"""
    try:
        resp = await client.get(
            "https://kream.co.kr/market",
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
            timeout=10,
        )
        # product name 패턴 추출
        names = re.findall(r'"translated_name"\s*:\s*"([^"]+)"', resp.text)
        brands = re.findall(r'"brand_name"\s*:\s*"([^"]+)"', resp.text)
        products = []
        for i, name in enumerate(names[:50]):
            products.append({"name": name, "brand": brands[i] if i < len(brands) else "", "source": "kream"})
        logger.info(f"[KREAM] HTML fallback: {len(products)}개 제품")
        return products
    except Exception as e:
        logger.warning(f"[KREAM] HTML 파싱 실패: {e}")
        return []


# ─────────────────────────────────────────────────────────────
# DB 조작 (supabase-py 경유)
# ─────────────────────────────────────────────────────────────
def _get_sb():
    from app.db_supabase import get_supabase
    return get_supabase()


def _seed_watchlist_if_empty():
    """초기 실행 시 INITIAL_WATCHLIST 데이터 삽입"""
    sb = _get_sb()
    count = sb.table("product_watchlist").select("id", count="exact").execute().count or 0
    if count > 0:
        logger.info(f"[워치리스트] 기존 {count}개 제품 존재 — 시드 스킵")
        return
    logger.info(f"[워치리스트] 초기 시드 ({len(INITIAL_WATCHLIST)}개) 삽입 중...")
    sb.table("product_watchlist").insert(INITIAL_WATCHLIST).execute()
    logger.info("✅ 워치리스트 시드 완료")


def _log_price(watchlist_id: int, lprice: int, hprice: int):
    sb = _get_sb()
    sb.table("watchlist_price_log").insert({
        "watchlist_id": watchlist_id,
        "lprice": lprice,
        "hprice": hprice,
    }).execute()


def _get_avg_30d(watchlist_id: int) -> int:
    """30일 평균 lprice 계산"""
    sb = _get_sb()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    res = sb.table("watchlist_price_log") \
        .select("lprice") \
        .eq("watchlist_id", watchlist_id) \
        .gte("checked_at", cutoff) \
        .execute()
    prices = [r["lprice"] for r in (res.data or [])]
    return int(sum(prices) / len(prices)) if prices else 0


def _cleanup_old_logs():
    """90일 이상 오래된 로그 삭제"""
    sb = _get_sb()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    sb.table("watchlist_price_log").delete().lt("checked_at", cutoff).execute()


# ─────────────────────────────────────────────────────────────
# 메인: 가격 모니터링 & 딜 자동 등록
# ─────────────────────────────────────────────────────────────
async def run_watchlist_monitor():
    """
    10분마다 실행:
    1. 활성 워치리스트 로드
    2. Naver lprice 조회
    3. 30일 평균 대비 alert_threshold% 이상 하락 → 딜 자동 등록
    """
    import app.db_supabase as db

    # 초기 시드 (최초 1회)
    _seed_watchlist_if_empty()

    sb = _get_sb()
    items_res = sb.table("product_watchlist").select("*").eq("is_active", True).execute()
    items = items_res.data or []
    if not items:
        logger.info("[워치리스트] 활성 제품 없음")
        return

    logger.info(f"[워치리스트] {len(items)}개 제품 가격 체크 시작")
    created = checked = 0

    async with httpx.AsyncClient(timeout=10) as client:
        for item in items:
            try:
                lprice, hprice, image_url = await _naver_lprice(item["search_query"], client)
                if lprice <= 0:
                    continue
                checked += 1

                # 가격 로그 저장
                _log_price(item["id"], lprice, hprice)

                # 30일 평균 계산
                avg = _get_avg_30d(item["id"])

                # 평균 업데이트
                sb.table("product_watchlist").update({
                    "current_lprice": lprice,
                    "avg_30d_lprice": avg if avg > 0 else lprice,
                    "last_checked_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", item["id"]).execute()

                # ── 딜 조건 판단 ───────────────────────────
                # 기준가: msrp > 0이면 msrp, 없으면 avg_30d
                base_price = item["msrp"] if item["msrp"] > 0 else avg
                if base_price <= 0 or lprice <= 0:
                    continue

                # 최소 가격 검증 (가품 의심 방지)
                if item["min_price"] > 0 and lprice < item["min_price"]:
                    logger.debug(f"[워치리스트skip] 최소가 미달: {item['name']} lprice={lprice:,} min={item['min_price']:,}")
                    continue

                threshold = item["alert_threshold"] or 15
                discount_rate = round((1 - lprice / base_price) * 100, 1)

                if discount_rate < threshold:
                    continue

                # ── 이미 같은 제품 active 딜 있으면 스킵 ──
                existing = sb.table("deals") \
                    .select("id, sale_price") \
                    .ilike("title", f"%{item['name'][:15]}%") \
                    .eq("status", "active") \
                    .execute()
                if existing.data:
                    ex_price = existing.data[0]["sale_price"]
                    if abs(ex_price - lprice) / lprice < 0.05:  # 5% 이내면 중복
                        continue
                    # 더 싸면 기존 만료하고 새 딜 등록
                    if lprice < ex_price:
                        sb.table("deals").update({"status": "expired"}).eq("id", existing.data[0]["id"]).execute()
                    else:
                        continue

                # ── 딜 제목 구성 ───────────────────────────
                brand_tag = f"[{item['brand']}] " if item.get("brand") else ""
                title = f"{brand_tag}{item['name']}"

                # ── 딜 등록 ───────────────────────────────
                db.create_deal({
                    "title": title,
                    "original_price": base_price,
                    "sale_price": lprice,
                    "discount_rate": discount_rate,
                    "image_url": image_url,
                    "product_url": f"https://search.shopping.naver.com/search/all?query={item['search_query'].replace(' ', '+')}",
                    "source": "naver",
                    "category": item["category"],
                    "status": "active",
                    "is_hot": discount_rate >= 25,
                    "submitter_name": item.get("brand", "정가파괴"),
                    "admin_note": f"워치리스트 자동: {discount_rate}% 하락 (기준:{base_price:,} 현재:{lprice:,})",
                })
                logger.info(
                    f"✅ [워치리스트] 딜 등록: {title} "
                    f"| -{discount_rate}% | 기준:{base_price:,} → 현재:{lprice:,}"
                )
                created += 1
                await asyncio.sleep(0.3)  # API 레이트 제한

            except ValueError as e:
                logger.debug(f"[워치리스트skip] 철칙 위반 — {e}")
            except Exception as e:
                logger.error(f"[워치리스트 오류] {item.get('name','')}: {e}")

    logger.info(f"✅ 워치리스트 완료: {checked}개 확인 | {created}개 딜 등록")
    _cleanup_old_logs()


# ─────────────────────────────────────────────────────────────
# 주 1회 KREAM 트렌딩 → 워치리스트 갱신
# ─────────────────────────────────────────────────────────────
async def run_kream_sync():
    """주 1회: KREAM 트렌딩 제품을 워치리스트에 추가"""
    async with httpx.AsyncClient(timeout=15) as client:
        products = await scrape_kream_trending(client)
        if not products:
            logger.warning("[KREAM] 트렌딩 제품 수집 실패")
            return

        sb = _get_sb()
        added = 0
        for p in products:
            name = p.get("name", "").strip()
            brand = p.get("brand", "").strip()
            if not name or len(name) < 4:
                continue

            # 이미 존재하는지 확인
            existing = sb.table("product_watchlist") \
                .select("id") \
                .ilike("name", f"%{name[:10]}%") \
                .execute()
            if existing.data:
                continue

            sb.table("product_watchlist").insert({
                "name": name,
                "search_query": f"{brand} {name}".strip() if brand else name,
                "brand": brand,
                "category": "기타",
                "source": "kream",
                "alert_threshold": 15,
            }).execute()
            added += 1

        logger.info(f"✅ [KREAM] 워치리스트 갱신: {added}개 신규 추가")
