"""
딜 품질 표준화 검증기 (DealValidator)

모든 수집 소스 (ppomppu / naver_cafe / naver / brand_deals)가
저장 전 이 검증기를 통과해야 합니다.

규칙 한 곳에서 관리 → 기준 변경 시 파일 하나만 수정.
"""
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 품질 기준 상수 (여기서만 수정)
# ──────────────────────────────────────────────
MIN_DISCOUNT_RATE   = 10.0   # 최소 할인율 (%)
MIN_PRICE_VS_NAVER  = 0.15   # 네이버 lprice의 15% 미만 → 가품/오류 의심
MAX_PRICE_VS_NAVER  = 1.05   # 네이버 lprice의 105% 초과 → 표시가격 부정확
HOT_THRESHOLD       = 20.0   # is_hot 기준 할인율 (%)

# 해외 소스 패턴
OVERSEAS_PATTERNS = [
    r"\[ebay\]", r"\[amazon", r"\[woot\]", r"\[costco\]",
    r"\[asus\.com\]", r"\[bestbuy\]", r"\[walmart\]", r"\[aliexpress\]",
    r"아마존재팬", r"\[미국 costco\]", r"\[amazon\.com\]",
]
_OVERSEAS_RE = re.compile("|".join(OVERSEAS_PATTERNS), re.IGNORECASE)

# 영어 제목 비율 (해외 딜 간접 차단 — Naver 매칭 오류 방지)
MAX_ENGLISH_RATIO = 0.6   # 영어 문자 비율 60% 초과 시 차단


# ──────────────────────────────────────────────
# 검증 결과
# ──────────────────────────────────────────────
@dataclass
class ValidationResult:
    valid: bool
    reason: Optional[str] = None
    # 보정된 값 (검증 통과 시 사용)
    original_price: float = 0.0
    sale_price: float = 0.0
    discount_rate: float = 0.0
    is_hot: bool = False
    naver_verified: bool = False
    warnings: list = field(default_factory=list)

    def __bool__(self):
        return self.valid


# ──────────────────────────────────────────────
# 메인 검증기
# ──────────────────────────────────────────────
class DealValidator:
    """
    딜 저장 전 표준 검증.

    사용법:
        v = DealValidator()
        result = await v.validate(item, naver_data=naver_result)
        if not result:
            continue  # 거부
        db.create_deal({..., "discount_rate": result.discount_rate, ...})
    """

    # ── 규칙 1: 해외 소스 차단 ──────────────────
    def _check_overseas(self, title: str) -> Optional[str]:
        if _OVERSEAS_RE.search(title):
            return f"해외 소스 감지: {title[:40]}"
        return None

    # ── 규칙 2: 영어 제목 비율 ──────────────────
    def _check_english_ratio(self, title: str) -> Optional[str]:
        if not title:
            return "제목 없음"
        alpha = sum(1 for c in title if c.isascii() and c.isalpha())
        ratio = alpha / max(len(title), 1)
        if ratio > MAX_ENGLISH_RATIO:
            return f"영어 제목 비율 과다 ({ratio:.0%}): {title[:40]}"
        return None

    # ── 규칙 3: 무료 딜 체크 (sale=0 허용) ──────
    def _is_free(self, sale_price: float) -> bool:
        return sale_price == 0

    # ── 규칙 4: 가격 기본 검증 ──────────────────
    def _check_prices(self, original: float, sale: float, dr: float) -> Optional[str]:
        if sale < 0:
            return f"판매가 음수: {sale}"
        if original <= 0 and sale > 0:
            return "원가 없음 (original_price=0)"
        if original > 0 and original <= sale:
            return f"원가({original:,.0f}) ≤ 판매가({sale:,.0f}) — 할인 없음"
        if original > 0 and sale > 0:
            calc_dr = (1 - sale / original) * 100
            if calc_dr < MIN_DISCOUNT_RATE:
                return f"할인율 미달: {calc_dr:.1f}% < {MIN_DISCOUNT_RATE}%"
        elif dr <= 0 and sale > 0:
            return f"할인율 0% (dr={dr})"
        return None

    # ── 규칙 5: 네이버 시세 대비 검증 ──────────
    def _check_naver_price(
        self, sale: float, naver_lprice: float, naver_hprice: Optional[float]
    ) -> tuple[Optional[str], Optional[str], float, float]:
        """
        Returns: (reject_reason, warning, corrected_original, corrected_dr)
        corrected_* = 0 means no correction
        """
        if not naver_lprice or naver_lprice <= 0:
            return None, None, 0, 0

        # 가품/오류 의심: 판매가가 네이버 최저가의 15% 미만
        if sale > 0 and sale < naver_lprice * MIN_PRICE_VS_NAVER:
            return f"가품 의심: {sale:,.0f}원 < 네이버 lprice({naver_lprice:,.0f}) × 15%", None, 0, 0

        # 정가 기준: hprice > lprice 이면 hprice 사용, 아니면 lprice
        naver_ref = (
            naver_hprice
            if (naver_hprice and naver_hprice > naver_lprice)
            else naver_lprice
        )

        # 판매가가 네이버 기준가보다 비쌈 → 딜 아님
        if sale >= naver_ref:
            return f"딜 아님: {sale:,.0f}원 ≥ 네이버 기준가({naver_ref:,.0f})", None, 0, 0

        corrected_dr = round((1 - sale / naver_ref) * 100, 1)

        # 할인율 기준 미달
        if corrected_dr < MIN_DISCOUNT_RATE:
            return f"할인율 미달(네이버 기준): {corrected_dr:.1f}%", None, 0, 0

        # 표시 가격이 네이버 최저가보다 5% 이상 비쌈 → 경고 (but not reject)
        warning = None
        if sale > naver_lprice * MAX_PRICE_VS_NAVER:
            warning = f"표시가({sale:,.0f}) > 네이버lprice({naver_lprice:,.0f}) — sale_price 보정됨"

        return None, warning, float(naver_ref), corrected_dr

    # ── 메인: 동기 검증 (Naver 데이터 없이) ────
    def validate_sync(self, item: dict) -> ValidationResult:
        """Naver API 없이 기본 검증만 (brand_deals 등에서 사용)"""
        title = item.get("title", "")
        sale = float(item.get("sale_price") or 0)
        orig = float(item.get("original_price") or 0)
        dr = float(item.get("discount_rate") or 0)
        is_free = self._is_free(sale)

        if not is_free:
            if err := self._check_overseas(title):
                return ValidationResult(valid=False, reason=f"[해외] {err}")
            if err := self._check_english_ratio(title):
                return ValidationResult(valid=False, reason=f"[영어] {err}")
            if err := self._check_prices(orig, sale, dr):
                return ValidationResult(valid=False, reason=f"[가격] {err}")

        # 할인율 재계산
        if is_free:
            final_dr, final_orig, final_sale = 100.0, 0.0, 0.0
        else:
            final_dr = round((1 - sale / orig) * 100, 1) if orig > sale > 0 else dr
            final_orig, final_sale = orig, sale

        return ValidationResult(
            valid=True,
            original_price=final_orig,
            sale_price=final_sale,
            discount_rate=final_dr,
            is_hot=final_dr >= HOT_THRESHOLD,
        )

    # ── 메인: 비동기 검증 (Naver 크로스체크 포함) ──
    async def validate(self, item: dict, naver_data: Optional[dict] = None) -> ValidationResult:
        """
        전체 검증. naver_data = search_product() 결과 dict.
        naver_data 없으면 validate_sync() 동등.
        """
        title = item.get("title", "")
        sale = float(item.get("sale_price") or 0)
        orig = float(item.get("original_price") or 0)
        dr = float(item.get("discount_rate") or 0)
        is_free = self._is_free(sale)

        if not is_free:
            if err := self._check_overseas(title):
                return ValidationResult(valid=False, reason=f"[해외] {err}")
            if err := self._check_english_ratio(title):
                return ValidationResult(valid=False, reason=f"[영어] {err}")

        warnings = []
        naver_verified = False
        final_orig, final_sale, final_dr = orig, sale, dr

        if not is_free and naver_data:
            naver_lprice = float(naver_data.get("naver_lprice") or 0)
            naver_hprice = float(naver_data.get("naver_hprice") or 0) or None

            if naver_lprice > 0:
                reject, warn, corrected_orig, corrected_dr = self._check_naver_price(
                    sale, naver_lprice, naver_hprice
                )
                if reject:
                    return ValidationResult(valid=False, reason=f"[네이버] {reject}")
                if warn:
                    warnings.append(warn)
                if corrected_orig > 0:
                    final_orig = corrected_orig
                    final_dr = corrected_dr
                    naver_verified = True
            else:
                # 네이버 결과 없음 → 기본 가격 검증으로 fallback
                if err := self._check_prices(orig, sale, dr):
                    return ValidationResult(valid=False, reason=f"[가격] {err}")
                if orig > sale > 0:
                    final_dr = round((1 - sale / orig) * 100, 1)
        else:
            if not is_free:
                if err := self._check_prices(orig, sale, dr):
                    return ValidationResult(valid=False, reason=f"[가격] {err}")
                if orig > sale > 0:
                    final_dr = round((1 - sale / orig) * 100, 1)

        return ValidationResult(
            valid=True,
            original_price=final_orig,
            sale_price=final_sale,
            discount_rate=final_dr,
            is_hot=final_dr >= HOT_THRESHOLD,
            naver_verified=naver_verified,
            warnings=warnings,
        )


# 싱글톤
validator = DealValidator()
