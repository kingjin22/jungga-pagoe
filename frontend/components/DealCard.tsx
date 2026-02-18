"use client";

import { useState } from "react";
import { Deal, formatPrice, getSourceLabel, getSourceColor, upvoteDeal } from "@/lib/api";
import DealModal from "./DealModal";

interface DealCardProps {
  deal: Deal;
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

export default function DealCard({ deal }: DealCardProps) {
  const [upvotes, setUpvotes] = useState(deal.upvotes);
  const [isHot, setIsHot] = useState(deal.is_hot);
  const [voted, setVoted] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);

  const handleUpvote = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (voted) return;
    try {
      const result = await upvoteDeal(deal.id);
      setUpvotes(result.upvotes);
      setIsHot(result.is_hot);
      setVoted(true);
    } catch (e) {
      console.error(e);
    }
  };

  const discountClass =
    deal.discount_rate >= 50
      ? "discount-high"
      : deal.discount_rate >= 30
      ? "discount-mid"
      : "discount-low";

  const targetUrl = deal.affiliate_url || deal.product_url;
  const savings = deal.original_price - deal.sale_price;
  const categoryEmoji = CATEGORY_EMOJI[deal.category] || "🛍️";

  // 만료일 계산
  const daysUntilExpiry = deal.expires_at
    ? Math.ceil(
        (new Date(deal.expires_at).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
      )
    : null;

  return (
    <>
      <div
        className="deal-card bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100 cursor-pointer"
        onClick={() => setModalOpen(true)}
      >
        {/* 이미지 */}
        <div className="relative h-48 bg-gray-100 overflow-hidden">
          {deal.image_url ? (
            <img
              src={deal.image_url}
              alt={deal.title}
              className="w-full h-full object-cover hover:scale-105 transition-transform duration-300"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-5xl bg-gradient-to-br from-gray-100 to-gray-200">
              {categoryEmoji}
            </div>
          )}

          {/* 뱃지들 */}
          <div className="absolute top-2 left-2 flex flex-col gap-1">
            {isHot && (
              <span className="hot-badge bg-[#E31E24] text-white text-xs font-bold px-2 py-0.5 rounded-full">
                🔥 HOT
              </span>
            )}
            <span
              className={`${getSourceColor(deal.source)} text-white text-xs font-bold px-2 py-0.5 rounded-full`}
            >
              {getSourceLabel(deal.source)}
            </span>
          </div>

          {/* 할인율 */}
          <div className="absolute top-2 right-2 bg-[#E31E24] text-white font-black text-lg px-2 py-1 rounded-xl leading-none">
            -{Math.round(deal.discount_rate)}%
          </div>

          {/* 만료일 뱃지 */}
          {daysUntilExpiry !== null && daysUntilExpiry > 0 && daysUntilExpiry <= 7 && (
            <div className="absolute bottom-2 right-2 bg-orange-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
              D-{daysUntilExpiry}
            </div>
          )}
        </div>

        {/* 내용 */}
        <div className="p-3">
          {/* 카테고리 태그 */}
          <div className="mb-1.5">
            <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full font-medium">
              {categoryEmoji} {deal.category}
            </span>
          </div>

          <h3 className="text-sm font-medium text-gray-800 line-clamp-2 hover:text-[#E31E24] transition-colors mb-2 leading-snug">
            {deal.title}
          </h3>

          {/* 가격 */}
          <div className="flex items-end gap-2 mb-1">
            <span className={`text-xl font-black ${discountClass}`}>
              {formatPrice(deal.sale_price)}
            </span>
            <span className="text-xs text-gray-400 line-through pb-0.5">
              {formatPrice(deal.original_price)}
            </span>
          </div>

          {/* 절약 금액 */}
          <p className="text-xs text-green-600 font-bold mb-2">
            💰 {formatPrice(savings)} 절약!
          </p>

          {/* 하단 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <span>👁 {deal.views.toLocaleString()}</span>
              {deal.submitter_name && (
                <span className="text-blue-500">by {deal.submitter_name}</span>
              )}
            </div>

            <button
              onClick={handleUpvote}
              disabled={voted}
              className={`flex items-center gap-1 text-sm px-3 py-1.5 rounded-full font-bold transition-all ${
                voted
                  ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                  : "bg-red-50 text-[#E31E24] hover:bg-[#E31E24] hover:text-white"
              }`}
            >
              👍 {upvotes}
            </button>
          </div>

          {/* 구매 버튼 */}
          <a
            href={targetUrl}
            target="_blank"
            rel="noopener noreferrer sponsored"
            onClick={(e) => e.stopPropagation()}
            className="mt-2 block w-full text-center bg-[#E31E24] text-white font-bold py-2 rounded-xl text-sm hover:bg-[#B71C1C] transition-colors"
          >
            지금 구매하기 →
          </a>
        </div>
      </div>

      {/* 상세 모달 */}
      <DealModal
        deal={modalOpen ? deal : null}
        onClose={() => setModalOpen(false)}
      />
    </>
  );
}
