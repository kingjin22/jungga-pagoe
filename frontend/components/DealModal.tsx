"use client";

import { useEffect, useState } from "react";
import { Deal, formatPrice, reportDeal, getDeal } from "@/lib/api";
import { trackEvent } from "@/lib/tracking";

function formatVerifiedTime(isoStr: string): string {
  try {
    const diff = Math.floor((Date.now() - new Date(isoStr).getTime()) / 60000);
    if (diff < 1) return "방금 확인";
    if (diff < 60) return `${diff}분 전 확인`;
    const h = Math.floor(diff / 60);
    return `${h}시간 전 확인`;
  } catch { return "최근 확인"; }
}

const SOURCE_LABEL: Record<string, string> = {
  coupang: "쿠팡",
  naver: "네이버",
  community: "커뮤니티",
};

interface DealModalProps {
  deal: Deal | null;
  onClose: () => void;
}

export default function DealModal({ deal, onClose }: DealModalProps) {
  const [reported, setReported] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [freshDeal, setFreshDeal] = useState<Deal | null>(null);

  // 모달 열릴 때 API 호출 → 조회수 증가 + 최신 데이터 + 트래킹
  useEffect(() => {
    if (!deal) { setFreshDeal(null); return; }
    setFreshDeal(deal); // 먼저 기존 데이터로 표시
    trackEvent("deal_open", deal.id);
    getDeal(deal.id).then(d => { if (d) setFreshDeal(d); }).catch(() => {});
  }, [deal?.id]);

  const handleReport = async () => {
    if (!deal || reported || reporting) return;
    setReporting(true);
    try {
      const res = await reportDeal(deal.id);
      setReported(true);
      if (res.hidden) onClose();
    } catch {}
    finally { setReporting(false); }
  };

  useEffect(() => {
    setReported(false); // 딜 바뀌면 신고 상태 초기화
  }, [deal?.id]);

  useEffect(() => {
    if (!deal) {
      document.body.style.overflow = "";
      return;
    }
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = "";
    };
  }, [deal?.id, onClose]);

  const d = freshDeal ?? deal;
  if (!d) return null;
  // 이하 deal → d 로 참조 (freshDeal 우선)

  const saved = d.original_price - d.sale_price;
  const targetUrl = d.affiliate_url || d.product_url;

  // Schema.org Product JSON-LD
  const productJsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: d.title,
    image: d.image_url,
    description: d.description || `${d.title} 최저가 할인`,
    offers: {
      "@type": "Offer",
      price: d.sale_price,
      priceCurrency: "KRW",
      availability: "https://schema.org/InStock",
      url: targetUrl,
      priceValidUntil: new Date(Date.now() + 86400000 * 3).toISOString().split("T")[0],
      ...(d.original_price > d.sale_price && {
        priceSpecification: {
          "@type": "PriceSpecification",
          price: d.original_price,
          priceCurrency: "KRW",
        },
      }),
    },
  };

  return (
    <>
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={d.title}
    >
      {/* 배경 */}
      <div
        className="absolute inset-0 bg-black/50"
        style={{ animation: "backdropFadeIn 0.2s ease both" }}
      />

      {/* 모달 — 모바일: 슬라이드업, 데스크톱: 스케일인 */}
      <div
        className="relative bg-white w-full sm:max-w-lg sm:mx-4 sm:rounded-sm max-h-[90vh] overflow-y-auto overscroll-contain"
        style={{
          animation: "slideUpModal 0.32s cubic-bezier(0.32, 0.72, 0, 1) both",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* 모바일 드래그 핸들 — 시트 상단에 인디케이터 표시 */}
        <div className="sm:hidden flex justify-center pt-3 pb-0.5" aria-hidden="true">
          <div className="w-10 h-1 rounded-full bg-gray-200" />
        </div>

        {/* 닫기 버튼 */}
        <button
          onClick={onClose}
          aria-label="닫기"
          className="absolute top-4 right-4 z-10 w-8 h-8 flex items-center justify-center text-gray-500 hover:text-gray-900 bg-white border border-gray-200"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>

        {/* 이미지 */}
        <div className="aspect-square bg-gray-100">
          {d.image_url ? (
            <img
              src={d.image_url}
              alt={d.title}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-6xl bg-gray-100">
              🛍️
            </div>
          )}
        </div>

        {/* 내용 */}
        <div className="p-5 modal-safe-bottom">
          {/* 메타 */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[11px] text-gray-400 font-medium">
              {SOURCE_LABEL[d.source] || d.source}
            </span>
            <span className="text-gray-200">|</span>
            <span className="text-[11px] text-gray-400">{d.category}</span>
            {d.submitter_name && (
              <>
                <span className="text-gray-200">|</span>
                <span className="text-[11px] text-gray-400">by {d.submitter_name}</span>
              </>
            )}
          </div>

          {/* 제목 */}
          <h2 className="text-base font-bold text-gray-900 leading-snug mb-3">
            {d.title}
          </h2>

          {/* 신뢰 뱃지 */}
          <div className="flex flex-wrap gap-1.5 mb-4">
            {d.source === "naver" ? (
              <>
                <span className="inline-flex items-center gap-1 text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded-sm font-medium">
                  ✓ MSRP 정가 대비 할인
                </span>
                <span className="inline-flex items-center gap-1 text-[10px] text-blue-700 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded-sm font-medium">
                  ✓ 네이버 최저가 기준
                </span>
              </>
            ) : (
              <>
                <span className="inline-flex items-center gap-1 text-[10px] text-orange-700 bg-orange-50 border border-orange-100 px-2 py-0.5 rounded-sm font-medium">
                  커뮤니티 제보 딜
                </span>
                <span className="inline-flex items-center gap-1 text-[10px] text-gray-600 bg-gray-50 border border-gray-100 px-2 py-0.5 rounded-sm font-medium">
                  판매처 가격 직접 확인 권장
                </span>
              </>
            )}
          </div>

          {/* 가격 */}
          <div className="bg-gray-50 p-4 mb-4">
            <div className="flex items-baseline gap-2 mb-1">
              {d.discount_rate > 0 && (
                <span className="text-2xl font-black text-[#E31E24]">
                  -{Math.round(d.discount_rate)}%
                </span>
              )}
              <span className="text-2xl font-black text-gray-900">
                {formatPrice(d.sale_price)}
              </span>
            </div>
            {d.discount_rate > 0 && (
              <>
                <p className="text-sm text-gray-400 line-through">
                  정가 {formatPrice(d.original_price)}
                </p>
                <p className="text-sm text-gray-600 mt-1 font-medium">
                  {formatPrice(saved)} 절약
                </p>
              </>
            )}
          </div>

          {/* 가격 검증 상태 */}
          {d.status === "price_changed" ? (
            <div className="bg-amber-50 border border-amber-200 px-4 py-3 mb-4">
              <p className="text-sm font-semibold text-amber-700 mb-0.5">⚠️ 가격이 변동되었습니다</p>
              <p className="text-xs text-amber-600">
                등록 당시 가격과 다를 수 있습니다.
                {d.verified_price && ` 최근 확인 가격: ${formatPrice(d.verified_price)}`}
              </p>
            </div>
          ) : (d as any).last_verified_at ? (
            <div className="flex items-center gap-1.5 mb-4">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span className="text-[11px] text-emerald-600 font-medium">
                가격 확인 완료
              </span>
              <span className="text-[11px] text-gray-400">
                · {formatVerifiedTime((d as any).last_verified_at)}
              </span>
            </div>
          ) : null}

          {/* 할인 신뢰지수 */}
          {(d as any).trust && (
            <div className="mb-4 p-3 bg-gray-50 rounded border border-gray-100">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-base">{(d as any).trust.emoji}</span>
                <span className="text-sm font-bold text-gray-800">
                  할인 신뢰지수 {(d as any).trust.score}점
                </span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${
                  (d as any).trust.score >= 90 ? "bg-red-100 text-red-600" :
                  (d as any).trust.score >= 75 ? "bg-green-100 text-green-600" :
                  (d as any).trust.score >= 60 ? "bg-blue-100 text-blue-600" :
                  "bg-gray-100 text-gray-500"
                }`}>
                  {(d as any).trust.label}
                </span>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed">
                {(d as any).trust.comment}
              </p>
              {(d as any).price_stats && (d as any).price_stats.data_days >= 7 && (
                <div className="mt-2 flex gap-3 text-xs text-gray-400">
                  <span>📉 {(d as any).price_stats.data_days}일 최저 {(d as any).price_stats.min_price.toLocaleString()}원</span>
                  <span>📊 평균 {(d as any).price_stats.avg_price.toLocaleString()}원</span>
                </div>
              )}
            </div>
          )}

          {/* 설명 */}
          {d.description && (
            <p className="text-sm text-gray-600 leading-relaxed mb-4 border-l-2 border-gray-200 pl-3">
              {d.description}
            </p>
          )}

          {/* 통계 */}
          <div className="flex gap-4 text-xs text-gray-400 mb-5">
            {(d.views ?? 0) >= 10 && <span>조회 {d.views!.toLocaleString()}</span>}
            {(d.upvotes ?? 0) >= 10 && <span>추천 {d.upvotes}</span>}
          </div>

          {/* 구매 버튼 */}
          {targetUrl ? (
            <a
              href={targetUrl}
              target="_blank"
              rel="noopener noreferrer sponsored"
              onClick={() => trackEvent("outbound_click", d.id)}
              className="block w-full text-center bg-[#111] text-white font-bold py-3.5 text-sm hover:bg-[#333] transition-colors"
            >
              {d.sale_price === 0 ? "지금 무료로 받기" : "지금 최저가 구매"}
            </a>
          ) : (
            <p className="block w-full text-center bg-gray-100 text-gray-400 font-bold py-3.5 text-sm">
              링크 준비 중
            </p>
          )}

          {d.affiliate_url && (
            <p className="text-[10px] text-gray-300 text-center mt-2">
              이 링크는 제휴 마케팅 링크입니다
            </p>
          )}

          {/* 가격 오류 신고 */}
          <div className="mt-4 pt-3 border-t border-gray-100 text-center">
            {reported ? (
              <p className="text-[11px] text-gray-400">신고가 접수되었습니다. 검토 후 처리됩니다.</p>
            ) : (
              <button
                onClick={handleReport}
                disabled={reporting}
                className="text-[11px] text-gray-300 hover:text-red-400 transition-colors underline-offset-2 hover:underline"
              >
                {reporting ? "신고 중..." : "가격 정보 오류 신고"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
    </>
  );
}
