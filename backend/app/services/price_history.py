"""
가격 히스토리 수집 + 할인 신뢰지수 계산

- 매일 1회 브랜드딜 42종 현재 네이버 최저가 스냅샷
- 90일 누적 후 → 3개월 최저가 / 평균가 비교
- 할인 신뢰지수: 역대최저 / 우수 / 보통
"""
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def _product_key(brand: str, query: str) -> str:
    """브랜드+쿼리를 고정 식별자로 변환"""
    raw = f"{brand.lower()}|{query.lower()}"
    return hashlib.md5(raw.encode()).hexdigest()[:16] + "_" + brand[:20].replace(" ", "_")


def save_price_snapshot(sb, brand: str, query: str, price: int) -> None:
    """현재가 스냅샷 저장 (하루 1회 중복 방지)"""
    key = _product_key(brand, query)
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    # 오늘 이미 저장된 스냅샷 있으면 스킵
    existing = (
        sb.table("price_history")
        .select("id")
        .eq("product_key", key)
        .gte("recorded_at", today_start)
        .limit(1)
        .execute()
        .data
    )
    if existing:
        return

    sb.table("price_history").insert({
        "product_key": key,
        "brand": brand,
        "query": query,
        "price": price,
        "source": "naver",
    }).execute()


def get_price_stats(sb, brand: str, query: str, days: int = 90) -> Optional[dict]:
    """
    최근 N일 가격 통계 반환
    {
        min_price: 역대 최저가,
        avg_price: 평균가,
        max_price: 최고가,
        data_days: 실제 데이터 보유 일수,
        trust_score: 신뢰지수 (0~100),
        trust_label: "역대최저" | "우수" | "양호" | "보통",
        trust_emoji: "🔥" | "✅" | "👍" | "💡",
        ai_comment: str,
    }
    """
    key = _product_key(brand, query)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    rows = (
        sb.table("price_history")
        .select("price,recorded_at")
        .eq("product_key", key)
        .gte("recorded_at", since)
        .order("recorded_at", desc=False)
        .execute()
        .data
    )

    if not rows:
        return None

    prices = [r["price"] for r in rows]
    min_p = min(prices)
    max_p = max(prices)
    avg_p = int(sum(prices) / len(prices))
    data_days = len(set(r["recorded_at"][:10] for r in rows))  # 유니크 날짜 수

    return {
        "min_price": min_p,
        "avg_price": avg_p,
        "max_price": max_p,
        "data_days": data_days,
        "chart": [{"date": r["recorded_at"][:10], "price": r["price"]} for r in rows],
    }


def calc_trust_score(current_price: int, stats: Optional[dict], msrp: int) -> dict:
    """
    할인 신뢰지수 계산
    - 히스토리 없으면 MSRP 비교만
    - 있으면 3개월 최저가/평균가 기준
    """
    if not stats or stats["data_days"] < 7:
        # 히스토리 부족 → MSRP 기준
        disc = (msrp - current_price) / msrp if msrp > 0 else 0
        if disc >= 0.30:
            return {"score": 60, "label": "양호", "emoji": "👍",
                    "comment": f"공식 정가 대비 {disc*100:.0f}% 할인. 가격 히스토리 수집 중입니다."}
        return {"score": 40, "label": "보통", "emoji": "💡",
                "comment": "가격 히스토리를 수집 중입니다. 추후 더 정확한 분석을 제공합니다."}

    min_p = stats["min_price"]
    avg_p = stats["avg_price"]
    days = stats["data_days"]

    # 역대 최저가 대비 %
    vs_min = (current_price - min_p) / min_p if min_p > 0 else 0
    # 평균가 대비 %
    vs_avg = (avg_p - current_price) / avg_p if avg_p > 0 else 0

    if vs_min <= 0.02:  # 역대 최저가 ±2%
        score = 95
        label = "역대최저"
        emoji = "🔥"
        comment = f"{days}일 중 역대 최저가 수준. 지금 사는 게 맞습니다."
    elif vs_avg >= 0.10:  # 평균보다 10% 이상 쌈
        score = 82
        label = "우수"
        emoji = "✅"
        comment = f"{days}일 평균가({avg_p:,}원) 대비 {vs_avg*100:.0f}% 저렴. 좋은 타이밍입니다."
    elif vs_avg >= 0.03:  # 평균보다 3% 이상 쌈
        score = 68
        label = "양호"
        emoji = "👍"
        comment = f"{days}일 평균가({avg_p:,}원)보다 약간 저렴한 수준입니다."
    else:
        score = 45
        label = "보통"
        emoji = "💡"
        comment = f"{days}일 평균가({avg_p:,}원)와 비슷한 가격입니다. 더 기다려볼 수 있습니다."

    return {"score": score, "label": label, "emoji": emoji, "comment": comment}


async def collect_daily_snapshots() -> int:
    """
    브랜드딜 전체 현재가 스냅샷 수집 (스케줄러에서 1일 1회 호출)
    """
    import httpx
    from app.db_supabase import get_supabase
    from app.services.brand_deals import PRODUCT_MSRP, NAVER_API_BASE, _get_naver_lprice

    sb = get_supabase()
    saved = 0
    errors = 0

    from app.config import settings
    if not settings.NAVER_CLIENT_ID:
        logger.error("NAVER_CLIENT_ID 없음")
        return 0
    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }

    async with httpx.AsyncClient() as client:
        for product in PRODUCT_MSRP:
            try:
                result = await _get_naver_lprice(product["query"], headers, client)
                if result:
                    lp, _, _, _ = result
                    save_price_snapshot(sb, product["brand"], product["query"], lp)
                    saved += 1
                    logger.debug(f"  스냅샷: {product['brand']} {product['query'][:30]} → {lp:,}원")
            except Exception as e:
                errors += 1
                logger.warning(f"  스냅샷 실패: {product['query'][:30]} — {e}")

    logger.info(f"[가격히스토리] 스냅샷 완료: {saved}개 저장 / {errors}개 실패")
    return saved
