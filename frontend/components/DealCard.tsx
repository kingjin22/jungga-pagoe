"use client";

import { useState, useEffect, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { Deal, formatPrice, upvoteDeal } from "@/lib/api";
import { trackEvent } from "@/lib/tracking";

interface DealCardProps {
  deal: Deal;
  onClick?: (deal: Deal) => void;
}

const CATEGORY_EMOJI: Record<string, string> = {
  "노트북/PC": "💻",
  "모니터/TV": "🖥️",
  "스마트폰": "📱",
  "태블릿": "📱",
  "이어폰/헤드폰": "🎧",
  "카메라": "📷",
  "가전": "🏠",
  "게임": "🎮",
  "네트워크": "📡",
  "패션/의류": "👗",
  "패션": "👗",
  "식품": "🍱",
  "뷰티": "💄",
  "홈리빙": "🏡",
  "건강": "💊",
  "도서": "📚",
  "소프트웨어": "💿",
  "스포츠": "⚽",
  "유아동": "🧸",
  "전자기기": "⚡",
  "기타": "📦",
};

function timeAgo(dateStr: string): string {
  const now = Date.now();
  const d = new Date(dateStr).getTime();
  const diff = now - d;
  const min = Math.floor(diff / 60000);
  if (min < 2) return "방금";
  if (min < 60) return `${min}분 전`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}시간 전`;
  const day = Math.floor(hr / 24);
  if (day < 7) return `${day}일 전`;
  return new Date(dateStr).toLocaleDateString("ko-KR", { month: "short", day: "numeric" });
}

// 쇼핑몰 이름 추출 (제목 앞 [XXX] 패턴)
function extractRetailer(title: string, submitterName?: string): string {
  const m = title.match(/^\[([^\]]{1,20})\]/);
  if (m) return m[1];
  if (submitterName && submitterName !== "뽐뿌") return submitterName;
  return "";
}

export default function DealCard({ deal, onClick }: DealCardProps) {
  const [upvotes, setUpvotes] = useState(deal.upvotes);
  const [voted, setVoted] = useState(false);
  const cardRef = useRef<HTMLDivElement>(null);
  const impressedRef = useRef(false);

  // 카드 노출 트래킹 (IntersectionObserver)
  useEffect(() => {
    if (!cardRef.current) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !impressedRef.current) {
          impressedRef.current = true;
          trackEvent("impression", deal.id);
        }
      },
      { threshold: 0.5 }
    );
    observer.observe(cardRef.current);
    return () => observer.disconnect();
  }, [deal.id]);

  const saved = deal.original_price - deal.sale_price;
  const targetUrl = deal.affiliate_url || deal.product_url;
  const isFree = deal.sale_price === 0;
  const retailer = extractRetailer(deal.title, deal.submitter_name);
  const brandSlug = retailer ? retailer.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") : "";
  const hasBrandPage = !!brandSlug && /^[a-z]/.test(brandSlug); // 영문 브랜드만

  const handleUpvote = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (voted) return;
    try {
      const result = await upvoteDeal(deal.id);
      setUpvotes(result.upvotes);
      setVoted(true);
    } catch {}
  };

  const handleCardClick = () => {
    trackEvent("deal_open", deal.id);
    onClick?.(deal);
  };

  return (
    <div ref={cardRef} className="deal-card group" onClick={handleCardClick}>
      {/* 이미지 영역 */}
      <div className="relative overflow-hidden bg-gray-100 aspect-square">
        {deal.image_url ? (
          <Image
            src={deal.image_url}
            alt={deal.title}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 20vw"
            className="object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl bg-gray-50">
            {CATEGORY_EMOJI[deal.category] || "📦"}
          </div>
        )}

        {/* 무료 뱃지 */}
        {isFree && (
          <div className="absolute top-0 left-0 bg-emerald-600 text-white text-sm font-black px-2 py-1 leading-none">
            FREE
          </div>
        )}

        {/* 할인율 뱃지 */}
        {!isFree && deal.discount_rate > 0 && (
          <div className="absolute top-0 left-0 bg-[#E31E24] text-white text-sm font-black px-2 py-1 leading-none">
            -{Math.round(deal.discount_rate)}%
          </div>
        )}

        {/* 가격변동 / HOT 뱃지 */}
        {deal.status === "price_changed" && (
          <div className="absolute top-0 right-0 bg-amber-500 text-white text-[10px] font-bold px-1.5 py-1 leading-none">
            가격변동
          </div>
        )}
        {deal.is_hot && deal.status !== "price_changed" && !isFree && (
          <div className="absolute top-0 right-0 bg-[#111] text-white text-[10px] font-bold px-1.5 py-1 leading-none">
            HOT
          </div>
        )}

        {/* 출처 칩 (리테일러 or 소스) — 브랜드 페이지 있으면 링크 */}
        <div className="absolute bottom-2 left-2 flex gap-1">
          {retailer && hasBrandPage ? (
            <Link
              href={`/brand/${brandSlug}`}
              onClick={(e) => e.stopPropagation()}
              className="bg-black/65 text-white text-[10px] font-medium px-1.5 py-0.5 leading-tight hover:bg-black/85 transition-colors"
            >
              {retailer}
            </Link>
          ) : retailer ? (
            <span className="bg-black/65 text-white text-[10px] font-medium px-1.5 py-0.5 leading-tight">
              {retailer}
            </span>
          ) : (
            <span className="bg-black/65 text-white text-[10px] font-medium px-1.5 py-0.5 leading-tight">
              {deal.source === "naver" ? "네이버" : deal.source === "coupang" ? "쿠팡" : "커뮤니티"}
            </span>
          )}
        </div>
      </div>

      {/* 텍스트 영역 */}
      <div className="pt-2 pb-3">
        {/* 카테고리 + 시간 */}
        <div className="flex items-center justify-between mb-0.5">
          <p className="text-[11px] text-gray-400">{deal.category}</p>
          {deal.created_at && (
            <p className="text-[10px] text-gray-300">{timeAgo(deal.created_at)}</p>
          )}
        </div>

        {/* 제목 */}
        <p className="text-[13px] text-gray-800 leading-snug line-clamp-2 mb-2 group-hover:text-black transition-colors">
          {deal.title}
        </p>

        {/* 가격 */}
        <div className="flex items-baseline gap-1.5 mb-1">
          {!isFree && deal.discount_rate > 0 && (
            <span className="text-[15px] font-black text-[#E31E24]">
              -{Math.round(deal.discount_rate)}%
            </span>
          )}
          <span className={`text-[15px] font-black ${isFree ? "text-emerald-600" : "text-gray-900"}`}>
            {isFree ? "무료" : formatPrice(deal.sale_price)}
          </span>
        </div>
        {!isFree && deal.discount_rate > 0 && deal.original_price > deal.sale_price && (
          <p className="price-original text-[12px]">
            {formatPrice(deal.original_price)}
          </p>
        )}

        {/* 절약 or 가격변동 */}
        {deal.status === "price_changed" && deal.verified_price ? (
          <p className="text-[11px] text-amber-600 mt-0.5 font-medium">
            현재가 {formatPrice(deal.verified_price)}
          </p>
        ) : saved > 100 ? (
          <p className="text-[11px] text-emerald-600 font-semibold mt-0.5">
            {formatPrice(saved)} 절약 ↓
          </p>
        ) : null}

        {/* 하단: 조회 + 추천 */}
        <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-100">
          {(deal.views ?? 0) >= 10 && (
            <span className="text-[11px] text-gray-400">
              조회 {deal.views!.toLocaleString()}
            </span>
          )}
          {(deal.views ?? 0) < 10 && <span />}
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
          onClick={(e) => { e.stopPropagation(); trackEvent("outbound_click", deal.id); }}
          className="block mt-2 text-center border border-gray-200 text-[12px] font-semibold py-2 text-gray-700 hover:border-gray-900 hover:text-black transition-colors"
        >
          {isFree ? "받으러 가기" : "지금 최저가 구매"}
        </a>
      </div>
    </div>
  );
}
