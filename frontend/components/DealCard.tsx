"use client";

import { useState } from "react";
import { Deal, formatPrice, getSourceLabel, upvoteDeal } from "@/lib/api";

interface DealCardProps {
  deal: Deal;
  onClick?: (deal: Deal) => void;
}

const SOURCE_LABEL: Record<string, string> = {
  coupang: "쿠팡",
  naver: "네이버",
  community: "커뮤니티",
};

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

export default function DealCard({ deal, onClick }: DealCardProps) {
  const [upvotes, setUpvotes] = useState(deal.upvotes);
  const [voted, setVoted] = useState(false);

  const saved = deal.original_price - deal.sale_price;
  const targetUrl = deal.affiliate_url || deal.product_url;

  const handleUpvote = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (voted) return;
    try {
      const result = await upvoteDeal(deal.id);
      setUpvotes(result.upvotes);
      setVoted(true);
    } catch {}
  };

  return (
    <div
      className="deal-card group"
      onClick={() => onClick?.(deal)}
    >
      {/* 이미지 영역 */}
      <div className="relative overflow-hidden bg-gray-100 aspect-square">
        {deal.image_url ? (
          <img
            src={deal.image_url}
            alt={deal.title}
            className="deal-card-img w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl bg-gray-100">
            {CATEGORY_EMOJI[deal.category] || "📦"}
          </div>
        )}

        {/* 할인율 뱃지 */}
        <div className="absolute top-0 left-0 bg-[#E31E24] text-white text-sm font-black px-2 py-1 leading-none">
          -{Math.round(deal.discount_rate)}%
        </div>

        {/* HOT 뱃지 */}
        {deal.is_hot && (
          <div className="absolute top-0 right-0 bg-[#111] text-white text-[10px] font-bold px-1.5 py-1 leading-none">
            HOT
          </div>
        )}

        {/* 출처 뱃지 */}
        <div className="absolute bottom-2 left-2">
          <span className="bg-black/60 text-white text-[10px] font-medium px-1.5 py-0.5">
            {SOURCE_LABEL[deal.source] || deal.source}
          </span>
        </div>
      </div>

      {/* 텍스트 영역 */}
      <div className="pt-2 pb-3">
        {/* 카테고리 */}
        <p className="text-[11px] text-gray-400 mb-0.5">{deal.category}</p>

        {/* 제목 */}
        <p className="text-[13px] text-gray-800 leading-snug line-clamp-2 mb-2 group-hover:text-black transition-colors">
          {deal.title}
        </p>

        {/* 가격 */}
        <div className="flex items-baseline gap-1.5 mb-1">
          <span className="text-[15px] font-black text-[#E31E24]">
            -{Math.round(deal.discount_rate)}%
          </span>
          <span className="price-sale text-[15px]">
            {formatPrice(deal.sale_price)}
          </span>
        </div>
        <p className="price-original text-[12px]">
          {formatPrice(deal.original_price)}
        </p>

        {/* 절약 금액 */}
        <p className="text-[11px] text-gray-400 mt-0.5">
          {formatPrice(saved)} 절약
        </p>

        {/* 하단: 조회수 + 추천 */}
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-100">
          <span className="text-[11px] text-gray-400">
            조회 {deal.views.toLocaleString()}
          </span>
          <button
            onClick={handleUpvote}
            disabled={voted}
            className={`flex items-center gap-1 text-[11px] font-medium transition-colors ${
              voted ? "text-gray-300" : "text-gray-500 hover:text-[#E31E24]"
            }`}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill={voted ? "#E31E24" : "none"} stroke="currentColor" strokeWidth="2">
              <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z" />
              <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
            </svg>
            {upvotes}
          </button>
        </div>

        {/* 구매 링크 */}
        <a
          href={targetUrl}
          target="_blank"
          rel="noopener noreferrer sponsored"
          onClick={(e) => e.stopPropagation()}
          className="block mt-2 text-center border border-gray-200 text-[12px] font-semibold py-2 text-gray-700 hover:border-gray-900 hover:text-black transition-colors"
        >
          구매하기
        </a>
      </div>
    </div>
  );
}
