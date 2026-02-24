from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Request
from typing import Optional
from app.schemas.deal import DealSubmitCommunity, DealResponse, DealListResponse
from app.rate_limit import limiter
import app.db_supabase as db

router = APIRouter(prefix="/api/deals", tags=["deals"])


@router.get("/", response_model=DealListResponse)
async def get_deals(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    offset: Optional[int] = Query(None, ge=0),
    category: Optional[str] = None,
    source: Optional[str] = None,
    sort: str = Query("latest", pattern="^(latest|popular|discount|price_asc|price_desc)$"),
    search: Optional[str] = None,
    hot_only: bool = False,
    brand: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
):
    return db.get_deals(
        page=page, size=size, category=category,
        source=source, sort=sort, search=search, hot_only=hot_only,
        brand=brand, offset=offset, price_min=price_min, price_max=price_max,
    )


@router.get("/hot")
async def get_hot_deals():
    return db.get_hot_deals(limit=10)


@router.get("/trending")
async def get_trending_deals():
    """최근 48h 내 조회수 TOP 3 딜"""
    from datetime import datetime, timedelta, timezone
    sb = db.get_supabase()
    since = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    res = (
        sb.table("deals")
        .select("id,title,sale_price,original_price,discount_rate,image_url,source,category,is_hot,created_at,affiliate_url,product_url,status,views,upvotes,submitter_name,expires_at,verified_price,last_verified_at,updated_at")
        .eq("status", "active")
        .gte("created_at", since)
        .order("views", desc=True)
        .limit(3)
        .execute()
    )
    return [db._to_deal_dict(r) for r in (res.data or [])]


@router.get("/suggestions")
async def get_suggestions(q: str = ""):
    """검색어 자동완성 — 브랜드명 + 카테고리 + 제목에서 추출"""
    if len(q) < 1:
        return []
    sb = db.get_supabase()
    res = (
        sb.table("deals")
        .select("title,category,submitter_name")
        .eq("status", "active")
        .ilike("title", f"%{q}%")
        .limit(20)
        .execute()
    )

    seen: set = set()
    suggestions = []
    for row in (res.data or []):
        # 카테고리 매칭
        cat_val = row.get("category")
        if cat_val and q.lower() in cat_val.lower() and cat_val not in seen:
            seen.add(cat_val)
            suggestions.append({"type": "category", "value": cat_val})
        # 제목 앞 3단어
        title = row.get("title", "")
        short = " ".join(title.split()[:3])[:20]
        if short and q.lower() in short.lower() and short not in seen:
            seen.add(short)
            suggestions.append({"type": "title", "value": short})
    return suggestions[:8]


@router.get("/by-ids")
async def get_deals_by_ids(ids: str = ""):
    """찜 목록용: 콤마구분 ID로 딜 조회"""
    if not ids:
        return []
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()][:50]
    if not id_list:
        return []
    sb = db.get_supabase()
    res = sb.table("deals").select("*").in_("id", id_list).execute()
    return [db._to_deal_dict(r) for r in (res.data or [])]


@router.get("/{deal_id}/related")
async def get_related_deals(deal_id: int):
    """같은 카테고리에서 최신 3개 추천 (자기 자신 제외)"""
    sb = db.get_supabase()
    cur = sb.table("deals").select("category").eq("id", deal_id).limit(1).execute()
    if not cur.data:
        return []
    category = cur.data[0].get("category", "기타")
    res = (
        sb.table("deals")
        .select("id,title,sale_price,original_price,discount_rate,image_url,source,category,is_hot,created_at,affiliate_url,product_url,status,upvotes,views,submitter_name,expires_at,verified_price,last_verified_at,updated_at")
        .eq("status", "active")
        .eq("category", category)
        .neq("id", deal_id)
        .order("created_at", desc=True)
        .limit(3)
        .execute()
    )
    return [db._to_deal_dict(r) for r in (res.data or [])]


@router.get("/{deal_id}/price-history")
async def get_price_history(deal_id: int):
    from app.db_supabase import get_supabase
    sb = get_supabase()
    try:
        res = sb.table("deal_price_log").select("price,recorded_at").eq("deal_id", deal_id).order("recorded_at").limit(60).execute()
        return res.data or []
    except Exception:
        return []


@router.get("/{deal_id}")
async def get_deal(deal_id: int):
    deal = db.get_deal_by_id(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")
    db.increment_views(deal_id)
    deal["views"] += 1

    # 가격 히스토리 + 신뢰지수 (네이버 소스만)
    if deal.get("source") == "naver":
        try:
            from app.services.price_history import get_price_stats, calc_trust_score
            import re
            sb = db.get_supabase()
            # brand: submitter_name 또는 title의 [Brand] 태그에서 추출
            brand = deal.get("submitter_name") or ""
            if not brand:
                m = re.match(r'^\[([^\]]+)\]', deal.get("title", ""))
                brand = m.group(1) if m else ""
            query = re.sub(r'^\[[^\]]+\]\s*', '', deal.get("title", ""))
            stats = get_price_stats(sb, brand, query)
            trust = calc_trust_score(
                int(deal.get("sale_price", 0)),
                stats,
                int(deal.get("original_price", 0))
            )
            deal["price_stats"] = stats
            deal["trust"] = trust

            # 차트용 히스토리 (날짜별 price 배열)
            try:
                import hashlib
                product_key = hashlib.md5(f"{brand}|{query}".encode()).hexdigest()[:16]
                rows = (
                    sb.table("price_history")
                    .select("price,recorded_at")
                    .eq("product_key", product_key)
                    .order("recorded_at")
                    .execute()
                    .data
                ) or []
                chart_data = []
                for r in rows:
                    dt = r["recorded_at"][:10]   # "2026-02-19"
                    mo, day = dt[5:7], dt[8:10]
                    chart_data.append({"date": f"{mo}/{day}", "price": int(r["price"])})
                deal["chart_data"] = chart_data
            except Exception:
                deal["chart_data"] = []
        except Exception:
            pass

    return deal


@router.post("/{deal_id}/upvote")
@limiter.limit("10/minute")  # IP당 1분에 10회 제한
async def upvote_deal(request: Request, deal_id: int):
    result = db.upvote_deal(deal_id)
    if not result:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")
    return result


@router.post("/submit")
@limiter.limit("3/10minutes")  # IP당 10분에 3회 제한
async def submit_community_deal(
    request: Request,
    deal_data: DealSubmitCommunity,
    background_tasks: BackgroundTasks,
):
    orig = deal_data.original_price
    sale = deal_data.sale_price
    discount_rate = round((1 - sale / orig) * 100, 1) if orig > 0 else 0

    if discount_rate < 10:
        raise HTTPException(status_code=400, detail="할인율이 10% 이상인 딜만 제보 가능합니다")

    from app.services.categorizer import infer_category
    # 카테고리 미입력 또는 기타 → 자동 분류 시도
    category = deal_data.category if deal_data.category and deal_data.category != "기타" \
        else infer_category(deal_data.title)

    # pending으로 저장 — 심사 전 노출 금지
    sb = db.get_supabase()
    res = sb.table("deals").insert({
        "title": deal_data.title,
        "description": deal_data.description,
        "original_price": orig,
        "sale_price": sale,
        "discount_rate": discount_rate,
        "image_url": deal_data.image_url,
        "product_url": deal_data.product_url,
        "category": category,
        "source": "community",
        "submitter_name": deal_data.submitter_name or "익명",
        "status": "pending",
        "is_hot": False,
        "admin_note": "제보 대기 — 자동 가격 검증 중",
    }).execute()
    deal = res.data[0]

    # 백그라운드: 자동 가격 검증
    background_tasks.add_task(_verify_submitted_deal, deal["id"], deal_data.product_url, sale)

    return {"id": deal["id"], "status": "pending", "message": "제보가 접수됐습니다. 검토 후 등록됩니다."}


@router.patch("/{deal_id}/expire")
async def expire_deal(deal_id: int):
    result = db.expire_deal(deal_id)
    if not result:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")
    return {"id": deal_id, "status": "expired"}


@router.post("/sync/naver")
async def sync_naver_deals():
    from app.services.naver import collect_real_deals
    deals_data = await collect_real_deals(limit_per_keyword=8)
    created = 0
    for item in deals_data:
        if db.deal_url_exists(item["product_url"]):
            continue
        orig = item.get("original_price", 0)
        sale = item.get("sale_price", 0)
        if orig <= 0 or sale <= 0:
            continue
        discount_rate = round((1 - sale / orig) * 100, 1)
        if discount_rate < 10:
            continue
        db.create_deal({
            "title": item["title"],
            "original_price": orig,
            "sale_price": sale,
            "discount_rate": discount_rate,
            "image_url": item.get("image_url"),
            "product_url": item["product_url"],
            "source": "naver",
            "category": item.get("category", "기타"),
            "status": "active",
            "is_hot": discount_rate >= 40,
        })
        created += 1
    return {"synced": created, "message": f"{created}개 네이버 딜 동기화 완료"}


@router.post("/sync/ppomppu")
async def sync_ppomppu_deals():
    """
    ⛔ 비활성화: Playwright 검증 없이 저장하던 레거시 엔드포인트
    - discount_rate=0 딜 대량 생성 원인 (식품 필터 미적용, orig==sale 허용)
    - 대신 스케줄러 _sync_ppomppu() 사용 (10분 주기, Playwright 가격 검증)
    """
    from fastapi import HTTPException
    raise HTTPException(
        status_code=410,
        detail="이 엔드포인트는 비활성화됐습니다. 뽐뿌 수집은 스케줄러가 자동으로 처리합니다."
    )


@router.post("/sync/coupang")
async def sync_coupang_deals():
    from app.services.coupang import get_best_deals
    deals_data = await get_best_deals(limit=30)
    created = 0
    for item in deals_data:
        if db.deal_url_exists(item["product_url"]):
            continue
        orig = item.get("original_price", 0)
        sale = item.get("sale_price", 0)
        if orig <= 0 or sale <= 0:
            continue
        discount_rate = round((1 - sale / orig) * 100, 1)
        if discount_rate < 5:
            continue
        db.create_deal({
            "title": item["title"],
            "original_price": orig,
            "sale_price": sale,
            "discount_rate": discount_rate,
            "image_url": item.get("image_url"),
            "product_url": item["product_url"],
            "affiliate_url": item.get("affiliate_url"),
            "source": "coupang",
            "status": "active",
            "is_hot": discount_rate >= 40,
        })
        created += 1
    return {"synced": created, "message": f"{created}개 쿠팡 딜 동기화 완료"}


async def _convert_to_affiliate_bg(product_url: str, payload: dict):
    from app.services.coupang import get_affiliate_link
    affiliate_url = await get_affiliate_link(product_url)
    if affiliate_url and affiliate_url != product_url:
        sb = db.get_supabase()
        sb.table("deals").update({"affiliate_url": affiliate_url}).eq("product_url", product_url).execute()


async def _fetch_naver_image(title: str) -> Optional[str]:
    """상품명으로 Naver 쇼핑 검색 → 첫 번째 이미지 URL 반환"""
    try:
        import urllib.request, urllib.parse, json, re as _re
        from app.config import settings
        headers = {
            "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
        }
        query = urllib.parse.urlencode({"query": title, "display": 3, "sort": "sim"})
        req = urllib.request.Request(
            f"https://openapi.naver.com/v1/search/shop.json?{query}", headers=headers
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            items = json.loads(r.read()).get("items", [])
        if items:
            return items[0].get("image", "")
    except Exception:
        pass
    return None


async def _verify_submitted_deal(deal_id: int, product_url: str, submitted_price: float):
    """
    제보 딜 자동 가격 검증 (백그라운드)
    - URL로 Naver 상품 검색 → lprice 비교
    - ±15% 이내면 auto_verified → 어드민 검토 대기
    - 명백 불일치 → auto_rejected
    - 이미지 없으면 Naver에서 자동 주입
    """
    import httpx, re
    from app.config import settings

    sb = db.get_supabase()

    async def _set_note(note: str, status: str = "pending"):
        sb.table("deals").update({"admin_note": note, "status": status}).eq("id", deal_id).execute()

    try:
        # 0) 이미지 자동 주입 (없는 경우) + 이미 만료된 딜 스킵
        deal_row = sb.table("deals").select("title, image_url, status").eq("id", deal_id).limit(1).execute().data
        if deal_row and deal_row[0].get("status") in ("expired", "rejected"):
            return  # 이미 만료/거부된 딜 → 검증 스킵
        if deal_row and not (deal_row[0].get("image_url") or ""):
            title = deal_row[0].get("title", "")
            image = await _fetch_naver_image(title)
            if image:
                sb.table("deals").update({"image_url": image}).eq("id", deal_id).execute()

        # 1) 쿠팡/네이버/일반 쇼핑몰 URL — httpx로 페이지 가져와서 가격 파싱 시도
        actual_price = None
        async with httpx.AsyncClient(
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
            follow_redirects=True,
        ) as client:
            try:
                resp = await client.get(product_url)
                text = resp.text
                # 가격 패턴 추출 (원 단위, 콤마 포함)
                prices = re.findall(r'[\"\'>](\d{1,3}(?:,\d{3})+)(?:원|<)', text)
                candidates = []
                for p in prices:
                    val = int(p.replace(",", ""))
                    if val >= 1000:
                        candidates.append(val)
                if candidates:
                    # 제보가와 가장 가까운 값
                    actual_price = min(candidates, key=lambda x: abs(x - submitted_price))
            except Exception:
                pass

        # 2) 검증 결과 판단
        if actual_price is None:
            # 크롤링 실패 → 어드민 수동 검토
            await _set_note("⚠️ 자동 검증 실패 — 수동 확인 필요", "pending")
            return

        diff = abs(actual_price - submitted_price) / submitted_price
        if diff <= 0.15:
            # ✅ 가격 일치 → 자동 승인 대기 (어드민 확인 후 최종 승인)
            await _set_note(
                f"✅ 자동 검증 통과 — 제보:{submitted_price:,.0f}원 / 실제:{actual_price:,.0f}원 ({diff*100:.0f}% 오차)\n"
                "어드민 최종 승인 대기 중"
            )
        else:
            # ❌ 가격 불일치 → 자동 거부
            await _set_note(
                f"❌ 자동 거부 — 가격 불일치: 제보:{submitted_price:,.0f}원 / 실제:{actual_price:,.0f}원 ({diff*100:.0f}% 오차)",
                "rejected",
            )

    except Exception as e:
        await _set_note(f"⚠️ 검증 오류: {e}")


@router.post("/{deal_id}/report")
@limiter.limit("5/minute")  # IP당 1분에 5회 제한
async def report_deal(request: Request, deal_id: int):
    """가격 오류 신고 — 3회 이상 신고 시 자동 숨김"""
    from fastapi import HTTPException
    sb = db.get_supabase()
    try:
        deal = sb.table("deals").select("id,report_count,status").eq("id", deal_id).limit(1).execute().data
    except Exception:
        deal = sb.table("deals").select("id,status").eq("id", deal_id).limit(1).execute().data

    if not deal:
        raise HTTPException(status_code=404, detail="딜을 찾을 수 없습니다")

    current = deal[0]
    new_count = (current.get("report_count") or 0) + 1
    patch = {}
    try:
        patch["report_count"] = new_count
    except Exception:
        pass

    if new_count >= 3:
        patch["status"] = "expired"

    if patch:
        try:
            sb.table("deals").update(patch).eq("id", deal_id).execute()
        except Exception:
            # report_count 컬럼 없을 경우 status만 업데이트
            if "status" in patch:
                sb.table("deals").update({"status": patch["status"]}).eq("id", deal_id).execute()

    return {"reported": True, "report_count": new_count, "hidden": new_count >= 3}
