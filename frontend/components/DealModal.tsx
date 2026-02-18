"use client";

import { useEffect } from "react";
import { Deal, formatPrice, getSourceLabel, getSourceColor } from "@/lib/api";

interface DealModalProps {
  deal: Deal | null;
  onClose: () => void;
}

const CATEGORY_EMOJI: Record<string, string> = {
  전자기기: "📱",
  패션: "👗",
  식품: "🍱",
  뷰티: "💄",
  홈리빙: "🏠",
  스포츠: "⚽",
  유아동: "🧒",
  기타: "📦",
};

export default function DealModal({ deal, onClose }: DealModalProps) {
  // ESC 키로 닫기
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  // 스크롤 잠금
  useEffect(() => {
    if (deal) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [deal]);

  if (!deal) return null;

  const targetUrl = deal.affiliate_url || deal.product_url;
  const savings = deal.original_price - deal.sale_price;
  const categoryEmoji = CATEGORY_EMOJI[deal.category] || "🛍️";

  const daysUntilExpiry = deal.expires_at
    ? Math.ceil(
        (new Date(deal.expires_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
      )
    : null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      {/* 배경 오버레이 */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* 모달 */}
      <div className="relative bg-white rounded-3xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* 닫기 버튼 */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 z-10 w-8 h-8 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded-full text-gray-600 transition-colors"
        >
          ✕
        </button>

        {/* 이미지 */}
        <div className="relative h-64 bg-gray-100 rounded-t-3xl overflow-hidden">
          {deal.image_url ? (
            <img
              src={deal.image_url}
              alt={deal.title}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-7xl bg-gradient-to-br from-gray-100 to-gray-200">
              {categoryEmoji}
            </div>
          )}

          {/* 뱃지들 */}
          <div className="absolute top-3 left-3 flex flex-col gap-1.5">
            {deal.is_hot && (
              <span className="bg-[#E31E24] text-white text-xs font-bold px-2.5 py-1 rounded-full">
                🔥 HOT
              </span>
            )}
            <span
              className={`${getSourceColor(deal.source)} text-white text-xs font-bold px-2.5 py-1 rounded-full`}
            >
              {getSourceLabel(deal.source)}
            </span>
          </div>

          {/* 할인율 */}
          <div className="absolute top-3 right-12 bg-[#E31E24] text-white font-black text-2xl px-3 py-1.5 rounded-2xl">
            -{Math.round(deal.discount_rate)}%
          </div>
        </div>

        {/* 내용 */}
        <div className="p-5">
          {/* 카테고리 + 만료일 */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-xs bg-gray-100 text-gray-600 px-2.5 py-1 rounded-full font-medium">
              {categoryEmoji} {deal.category}
            </span>
            {daysUntilExpiry !== null && daysUntilExpiry > 0 && (
              <span className="text-xs bg-orange-50 text-orange-600 border border-orange-200 px-2.5 py-1 rounded-full font-bold">
                D-{daysUntilExpiry}
              </span>
            )}
            {daysUntilExpiry !== null && daysUntilExpiry <= 0 && (
              <span className="text-xs bg-red-50 text-red-600 border border-red-200 px-2.5 py-1 rounded-full font-bold">
                만료됨
              </span>
            )}
          </div>

          {/* 제목 */}
          <h2 className="text-base font-bold text-gray-900 mb-4 leading-snug">
            {deal.title}
          </h2>

          {/* 가격 */}
          <div className="bg-gray-50 rounded-2xl p-4 mb-4">
            <div className="flex items-end gap-3 mb-1">
              <span className="text-3xl font-black text-[#E31E24]">
                {formatPrice(deal.sale_price)}
              </span>
              <span className="text-sm text-gray-400 line-through pb-1">
                {formatPrice(deal.original_price)}
              </span>
            </div>
            <p className="text-sm text-green-600 font-bold">
              💰 {formatPrice(savings)} 절약!
            </p>
          </div>

          {/* 설명 */}
          {deal.description && (
            <p className="text-sm text-gray-600 mb-4 leading-relaxed bg-blue-50 rounded-xl p-3">
              {deal.description}
            </p>
          )}

          {/* 메타 정보 */}
          <div className="flex items-center gap-4 text-xs text-gray-400 mb-4">
            <span>👁 {deal.views.toLocaleString()} 조회</span>
            <span>👍 {deal.upvotes} 추천</span>
            {deal.submitter_name && (
              <span className="text-blue-500 font-medium">
                제보: {deal.submitter_name}
              </span>
            )}
          </div>

          {/* 구매 버튼 */}
          <a
            href={targetUrl}
            target="_blank"
            rel="noopener noreferrer sponsored"
            className="block w-full text-center bg-[#E31E24] text-white font-black py-3.5 rounded-2xl text-base hover:bg-[#B71C1C] transition-colors"
          >
            🛒 구매하러 가기 →
          </a>

          {deal.affiliate_url && (
            <p className="text-center text-xs text-gray-400 mt-2">
              ✓ 파트너스 링크 (구매 시 소정의 수수료 지급)
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
