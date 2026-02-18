"use client";

import { useEffect } from "react";
import { Deal, formatPrice } from "@/lib/api";

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
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handler);
    document.body.style.overflow = deal ? "hidden" : "";
    return () => {
      document.removeEventListener("keydown", handler);
      document.body.style.overflow = "";
    };
  }, [deal, onClose]);

  if (!deal) return null;

  const saved = deal.original_price - deal.sale_price;
  const targetUrl = deal.affiliate_url || deal.product_url;

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center"
      onClick={onClose}
    >
      {/* 배경 */}
      <div className="absolute inset-0 bg-black/50" />

      {/* 모달 */}
      <div
        className="relative bg-white w-full sm:max-w-lg sm:mx-4 max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 닫기 버튼 */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 w-8 h-8 flex items-center justify-center text-gray-500 hover:text-gray-900 bg-white border border-gray-200"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>

        {/* 이미지 */}
        <div className="aspect-square bg-gray-100">
          {deal.image_url ? (
            <img
              src={deal.image_url}
              alt={deal.title}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-6xl bg-gray-100">
              🛍️
            </div>
          )}
        </div>

        {/* 내용 */}
        <div className="p-5">
          {/* 메타 */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[11px] text-gray-400 font-medium">
              {SOURCE_LABEL[deal.source] || deal.source}
            </span>
            <span className="text-gray-200">|</span>
            <span className="text-[11px] text-gray-400">{deal.category}</span>
            {deal.submitter_name && (
              <>
                <span className="text-gray-200">|</span>
                <span className="text-[11px] text-gray-400">by {deal.submitter_name}</span>
              </>
            )}
          </div>

          {/* 제목 */}
          <h2 className="text-base font-bold text-gray-900 leading-snug mb-4">
            {deal.title}
          </h2>

          {/* 가격 */}
          <div className="bg-gray-50 p-4 mb-4">
            <div className="flex items-baseline gap-2 mb-1">
              {deal.discount_rate > 0 && (
                <span className="text-2xl font-black text-[#E31E24]">
                  -{Math.round(deal.discount_rate)}%
                </span>
              )}
              <span className="text-2xl font-black text-gray-900">
                {formatPrice(deal.sale_price)}
              </span>
            </div>
            {deal.discount_rate > 0 && (
              <>
                <p className="text-sm text-gray-400 line-through">
                  정가 {formatPrice(deal.original_price)}
                </p>
                <p className="text-sm text-gray-600 mt-1 font-medium">
                  {formatPrice(saved)} 절약
                </p>
              </>
            )}
          </div>

          {/* 가격변동 경고 */}
          {deal.status === "price_changed" && (
            <div className="bg-amber-50 border border-amber-200 px-4 py-3 mb-4">
              <p className="text-sm font-semibold text-amber-700 mb-0.5">⚠️ 가격이 변동되었습니다</p>
              <p className="text-xs text-amber-600">
                등록 당시 가격과 다를 수 있습니다.
                {deal.verified_price && ` 현재 확인된 가격: ${formatPrice(deal.verified_price)}`}
              </p>
            </div>
          )}

          {/* 설명 */}
          {deal.description && (
            <p className="text-sm text-gray-600 leading-relaxed mb-4 border-l-2 border-gray-200 pl-3">
              {deal.description}
            </p>
          )}

          {/* 통계 */}
          <div className="flex gap-4 text-xs text-gray-400 mb-5">
            <span>조회 {deal.views.toLocaleString()}</span>
            <span>추천 {deal.upvotes}</span>
          </div>

          {/* 구매 버튼 */}
          <a
            href={targetUrl}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="block w-full text-center bg-[#111] text-white font-bold py-3.5 text-sm hover:bg-[#333] transition-colors"
          >
            지금 구매하기
          </a>

          {deal.affiliate_url && (
            <p className="text-[10px] text-gray-300 text-center mt-2">
              이 링크는 제휴 마케팅 링크입니다
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
