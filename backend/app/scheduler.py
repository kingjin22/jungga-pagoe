"""
APScheduler 백그라운드 자동 작업
- 매 30분  : 쿠팡 딜 sync
- 매 1시간 : 네이버 딜 sync
- 매 1시간 : 가격 검증 (등록된 딜 현재 가격 체크 → 가격 오르면 자동 비활성)
"""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def _sync_coupang():
    # 쿠팡 파트너스 API 승인 전까지 비활성화
    # 샘플 데이터(link.coupang.com/sample)는 이미지 없고 링크 불통 → 사용자 경험 최악
    # 파트너스 승인 후 partners.coupang.com에서 API 키 받아 활성화
    logger.info("⏸ 쿠팡 sync 비활성화 (파트너스 승인 대기 중)")
    return


async def _sync_naver():
    try:
        import app.db_supabase as db
        from app.services.naver import collect_real_deals
        from app.services.deal_validator import validator
        deals_data = await collect_real_deals(limit_per_keyword=5)
        created = skipped = 0
        for item in deals_data:
            if db.deal_url_exists(item["product_url"]):
                continue
            v = validator.validate_sync(item)
            if not v:
                logger.debug(f"[네이버skip] {v.reason}")
                skipped += 1
                continue
            # 제목+가격 중복 체크 (URL 달라도 동일 제품 방지)
            if db.deal_duplicate_exists(item["title"], v.sale_price):
                skipped += 1
                continue
            db.create_deal({
                "title": item["title"],
                "original_price": v.original_price,
                "sale_price": v.sale_price,
                "discount_rate": v.discount_rate,
                "image_url": item.get("image_url"),
                "product_url": item["product_url"],
                "source": "naver",
                "category": item.get("category", "기타"),
                "status": "active",
                "is_hot": v.is_hot,
            })
            created += 1
        logger.info(f"✅ 네이버 sync: {created}개 저장 | {skipped}개 제외")
    except Exception as e:
        logger.error(f"❌ 네이버 sync: {e}")


async def _sync_ppomppu():
    # ⛔ 커뮤니티 딜 수집 중단 — 네이버 키워드 검색 기반 가격 매칭 신뢰도 부족
    # 식품/일상용품은 키워드 매칭 오류로 hprice가 완전히 다른 제품 기준이 됨
    # TODO: 브랜드명+모델명 정확히 파싱 가능한 카테고리(전자기기/패션)만 선별 수집
    logger.info("⛔ 뽐뿌 sync 중단 — 가격 신뢰성 재설계 필요")
    return
    try:
        import app.db_supabase as db
        from app.services.ppomppu import fetch_ppomppu_deals
        from app.services.naver import search_product
        from app.services.deal_validator import validator

        deals_data = await fetch_ppomppu_deals()
        created = skipped = 0

        for item in deals_data:
            sale = item.get("sale_price", 0)
            is_free = sale == 0

            # 품질 기준: 이미지 + 실제 쇼핑몰 URL (무료 제외)
            if not is_free:
                has_image = bool(item.get("image_url"))
                has_real_url = bool(item.get("product_url") and "ppomppu.co.kr" not in item["product_url"])
                if not (has_image and has_real_url):
                    skipped += 1
                    continue

            if db.deal_url_exists(item["product_url"]):
                continue

            # 네이버 시세 조회 (무료딜 제외)
            naver_data = None
            if not is_free:
                try:
                    naver_data = await search_product(item["title"])
                except Exception as e:
                    logger.warning(f"네이버 조회 실패 [{item['title'][:30]}]: {e}")

            # DealValidator 통과 여부
            v = await validator.validate(item, naver_data=naver_data)
            if not v:
                logger.debug(f"[뽐뿌skip] {v.reason}")
                skipped += 1
                continue

            if v.warnings:
                for w in v.warnings:
                    logger.info(f"  ⚠️ {w}")

            # product_url = 네이버 카탈로그 URL 우선 (실시간 최저가 표시)
            # 없으면 원본 쇼핑몰 URL 사용
            naver_catalog_url = naver_data.get("product_url") if naver_data else None
            final_url = naver_catalog_url or item["product_url"]
            if not final_url:
                skipped += 1
                continue

            # 중복 체크는 최종 URL 기준
            if db.deal_url_exists(final_url):
                skipped += 1
                continue

            db.create_deal({
                "title": item["title"],
                "description": item.get("description"),
                "original_price": v.original_price,
                "sale_price": v.sale_price,
                "discount_rate": v.discount_rate,
                "image_url": item.get("image_url") or (naver_data.get("image_url") if naver_data else None),
                "product_url": final_url,
                "source": "community",
                "category": item.get("category", "기타"),
                "status": "active",
                "is_hot": v.is_hot,
                "submitter_name": item.get("submitter_name", "뽐뿌"),
                "admin_note": "네이버 카탈로그 + 시세 검증" if naver_catalog_url else "뽐뿌 직링크",
            })
            created += 1

        logger.info(f"✅ 뽐뿌 sync: {created}개 저장 | {skipped}개 제외")
    except Exception as e:
        logger.error(f"❌ 뽐뿌 sync: {e}")


async def _sync_naver_cafe():
    # ⛔ 커뮤니티 딜 수집 중단 — 식품/일상용품 키워드 매칭 신뢰도 부족
    logger.info("⛔ 정가거부 카페 sync 중단")
    return
    try:
        import app.db_supabase as db
        from app.services.naver_cafe import fetch_naver_cafe_deals

        deals_data = await fetch_naver_cafe_deals()
        created = skipped = 0

        from app.services.deal_validator import validator
        for item in deals_data:
            if db.deal_url_exists(item["product_url"]):
                skipped += 1
                continue

            v = validator.validate_sync(item)   # naver_cafe는 이미 내부에서 네이버 검증 완료
            if not v:
                logger.debug(f"[카페skip] {v.reason}")
                skipped += 1
                continue

            db.create_deal({
                "title": item["title"],
                "description": item.get("description"),
                "original_price": v.original_price,
                "sale_price": v.sale_price,
                "discount_rate": v.discount_rate,
                "image_url": item.get("image_url"),
                "product_url": item["product_url"],
                "source": "community",
                "category": item.get("category", "기타"),
                "status": "active",
                "is_hot": v.is_hot,
                "submitter_name": item.get("submitter_name", "정가거부"),
                "admin_note": "정가거부 카페 + 네이버 시세 검증",
            })
            created += 1

        logger.info(f"✅ 정가거부 카페: {created}개 신규 | {skipped}개 중복 스킵")
    except Exception as e:
        logger.error(f"❌ 정가거부 카페 sync: {e}")


async def _verify_prices():
    logger.info("🔍 가격 검증 시작...")
    try:
        import app.db_supabase as db
        from app.services.price_checker import verify_deal, MAX_FAIL_COUNT
        from datetime import datetime, timedelta
        cutoff = (datetime.utcnow() - timedelta(minutes=55)).isoformat()
        deals = db.get_deals_for_verify(cutoff)
        logger.info(f"  검증 대상: {len(deals)}개")
        ok = changed = expired_count = 0
        for deal in deals:
            try:
                check = await verify_deal(deal)
                patch = {"last_verified_at": check["last_verified_at"].isoformat()}
                if check["verified_price"] is not None:
                    patch["verified_price"] = check["verified_price"]
                action = check["action"]
                fail = int(deal.get("verify_fail_count") or 0)
                if action == "url_dead":
                    fail += 1; patch["verify_fail_count"] = fail
                    if fail >= MAX_FAIL_COUNT: patch["status"] = "expired"; expired_count += 1
                elif action == "expired":
                    patch["status"] = "expired"; patch["verify_fail_count"] = 0; expired_count += 1
                elif action == "price_changed":
                    patch["status"] = "price_changed"; patch["verify_fail_count"] = 0; changed += 1
                elif action == "price_dropped":
                    # 네이버 최저가 < 우리 표시가 → sale_price 업데이트 (정확성 유지 핵심!)
                    new_price = check["verified_price"]
                    orig = float(deal.get("original_price") or 0)
                    patch["sale_price"] = new_price
                    patch["status"] = "active"
                    patch["verify_fail_count"] = 0
                    if orig > 0 and new_price < orig:
                        patch["discount_rate"] = round((1 - new_price / orig) * 100, 1)
                    ok += 1
                    logger.info(f"    ↓ 가격 업데이트: {int(deal.get('sale_price',0)):,} → {int(new_price):,}원")
                else:
                    patch["status"] = "active"; patch["verify_fail_count"] = 0; ok += 1
                db.update_deal_verify(deal["id"], patch)
            except Exception as e:
                logger.error(f"  딜 #{deal.get('id')} 검증 오류: {e}")
        logger.info(f"✅ 가격 검증 완료 — 정상:{ok} 변동:{changed} 만료:{expired_count}")
    except Exception as e:
        logger.error(f"❌ 가격 검증 오류: {e}")


async def _sync_brand_deals():
    """브랜드 공식 정가 × 네이버 현재가 비교 → 실제 할인 딜"""
    try:
        import app.db_supabase as db
        from app.services.brand_deals import collect_brand_deals
        from app.services.deal_validator import validator
        deals_data = await collect_brand_deals(min_discount=10)
        created = skipped = 0
        for item in deals_data:
            if db.deal_url_exists(item["product_url"]):
                continue
            v = validator.validate_sync(item)
            if not v:
                logger.debug(f"[브랜드skip] {v.reason}")
                skipped += 1
                continue
            # 제목+가격 중복 체크
            if db.deal_duplicate_exists(item["title"], v.sale_price):
                skipped += 1
                continue
            db.create_deal({
                "title": item["title"],
                "description": item.get("description"),
                "original_price": v.original_price,
                "sale_price": v.sale_price,
                "discount_rate": v.discount_rate,
                "image_url": item.get("image_url"),
                "product_url": item["product_url"],
                "source": "naver",
                "category": item.get("category", "기타"),
                "status": "active",
                "is_hot": v.is_hot,
                "submitter_name": item.get("brand", ""),
            })
            created += 1
        logger.info(f"✅ 브랜드딜 sync: {created}개 저장 | {skipped}개 제외")
    except Exception as e:
        logger.error(f"❌ 브랜드딜 sync: {e}")


async def _expire_old_deals():
    """3일 이상 된 딜 자동 만료"""
    try:
        import app.db_supabase as db
        from datetime import datetime, timezone, timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        sb = db.get_supabase()
        result = sb.table("deals").update({"status": "expired"}).eq("status", "active").lt("created_at", cutoff).execute()
        count = len(result.data) if result.data else 0
        if count:
            logger.info(f"✅ 오래된 딜 만료: {count}개")
    except Exception as e:
        logger.error(f"❌ 딜 만료 처리 오류: {e}")


async def _collect_price_snapshots():
    """일일 가격 스냅샷 (브랜드딜 42종 현재가 저장)"""
    try:
        from app.services.price_history import collect_daily_snapshots
        saved = await collect_daily_snapshots()
        logger.info(f"[스냅샷] {saved}개 저장")
    except Exception as e:
        logger.error(f"[스냅샷] 오류: {e}")


def start_scheduler():
    """스케줄러 시작"""
    scheduler.add_job(
        _sync_coupang,
        trigger=IntervalTrigger(minutes=30),
        id="sync_coupang",
        name="쿠팡 딜 자동 동기화",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_naver,
        trigger=IntervalTrigger(hours=1),
        id="sync_naver",
        name="네이버 딜 자동 동기화",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_ppomppu,
        trigger=IntervalTrigger(minutes=30),
        id="sync_ppomppu",
        name="뽐뿌 핫딜 자동 동기화",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_naver_cafe,
        trigger=IntervalTrigger(minutes=30),
        id="sync_naver_cafe",
        name="정가거부 카페 핫딜 수집 (30분)",
        replace_existing=True,
    )
    scheduler.add_job(
        _verify_prices,
        trigger=IntervalTrigger(minutes=30),
        id="verify_prices",
        name="가격 검증 (30분마다)",
        replace_existing=True,
    )
    scheduler.add_job(
        _sync_brand_deals,
        trigger=IntervalTrigger(hours=2),
        id="sync_brand_deals",
        name="브랜드딜 정가 비교 동기화 (2h)",
        replace_existing=True,
    )
    scheduler.add_job(
        _expire_old_deals,
        trigger=IntervalTrigger(hours=6),
        id="expire_old_deals",
        name="오래된 딜 자동 만료 (3일 이상)",
        replace_existing=True,
    )
    scheduler.add_job(
        _collect_price_snapshots,
        trigger=IntervalTrigger(hours=24),
        id="price_snapshots",
        name="일일 가격 스냅샷 (브랜드딜 42종)",
        replace_existing=True,
    )
    scheduler.start()
    msg = "🕐 스케줄러 시작: 쿠팡(30분) / 네이버(1h) / 뽐뿌(30분) / 가격검증(1h) / 만료처리(6h)"
    logger.info(msg)
    print(msg, flush=True)  # uvicorn stdout에도 출력


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("🛑 스케줄러 종료")
