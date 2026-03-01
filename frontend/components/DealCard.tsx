"use client";

import { useState, useEffect, useRef } from "react";
import Image from "next/image";
import Link from "next/link";
import { Deal, formatPrice, upvoteDeal } from "@/lib/api";
import { trackEvent } from "@/lib/tracking";
import FavoriteButton from "./FavoriteButton";
import { useRecentDeals } from "@/hooks/useRecentDeals";

interface DealCardProps {
  deal: Deal;
  onClick?: (deal: Deal) => void;
  onDismiss?: (dealId: number) => void;
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

// 이미지 없는 카드에 카테고리별 그라데이션 배경 적용 (단조로운 회색 대신 시각적 구분)
const CATEGORY_GRADIENT: Record<string, string> = {
  "노트북/PC":     "from-blue-50 via-indigo-50 to-blue-100",
  "모니터/TV":     "from-slate-50 via-blue-50 to-slate-100",
  "스마트폰":      "from-sky-50 via-cyan-50 to-sky-100",
  "태블릿":        "from-sky-50 via-cyan-50 to-sky-100",
  "이어폰/헤드폰": "from-violet-50 via-purple-50 to-violet-100",
  "카메라":        "from-amber-50 via-yellow-50 to-amber-100",
  "가전":          "from-teal-50 via-emerald-50 to-teal-100",
  "게임":          "from-red-50 via-rose-50 to-red-100",
  "네트워크":      "from-cyan-50 via-sky-50 to-cyan-100",
  "패션/의류":     "from-rose-50 via-pink-50 to-rose-100",
  "패션":          "from-rose-50 via-pink-50 to-rose-100",
  "식품":          "from-orange-50 via-amber-50 to-orange-100",
  "뷰티":          "from-fuchsia-50 via-pink-50 to-fuchsia-100",
  "홈리빙":        "from-green-50 via-teal-50 to-green-100",
  "건강":          "from-lime-50 via-green-50 to-lime-100",
  "도서":          "from-yellow-50 via-amber-50 to-yellow-100",
  "소프트웨어":    "from-blue-50 via-indigo-50 to-blue-100",
  "스포츠":        "from-green-50 via-lime-50 to-emerald-100",
  "유아동":        "from-yellow-50 via-orange-50 to-yellow-100",
  "전자기기":      "from-indigo-50 via-blue-50 to-indigo-100",
  "기타":          "from-gray-50 via-slate-50 to-gray-100",
};

function TimeLeftBadge({ createdAt }: { createdAt: string }) {
  const [left, setLeft] = useState("");

  useEffect(() => {
    const update = () => {
      const diff = Date.now() - new Date(createdAt).getTime();
      const remaining = 24 * 3600 * 1000 - diff;
      if (remaining <= 0) { setLeft(""); return; }
      const h = Math.floor(remaining / 3600000);
      const m = Math.floor((remaining % 3600000) / 60000);
      if (h >= 12) setLeft("NEW");
      else if (h >= 1) setLeft(`⏱ ${h}시간`);
      else setLeft(`⏱ ${m}분`);
    };
    update();
    const t = setInterval(update, 60000);
    return () => clearInterval(t);
  }, [createdAt]);

  if (!left) return null;
  const isUrgent = left !== "NEW";
  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 ${
      isUrgent ? "bg-[#E31E24] text-white" : "bg-blue-500 text-white"
    }`}>
      {left}
    </span>
  );
}

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

export default function DealCard({ deal, onClick, onDismiss }: DealCardProps) {
  const [upvotes, setUpvotes] = useState(deal.upvotes);
  const [voted, setVoted] = useState(false);
  const [imgError, setImgError] = useState(false);
  const { addRecent } = useRecentDeals();
  const cardRef = useRef<HTMLDivElement>(null);
  const impressedRef = useRef(false);

  // 스와이프 상태
  const [swipeX, setSwipeX] = useState(0);
  const [isDismissing, setIsDismissing] = useState(false);
  const touchStartX = useRef<number | null>(null);
  const SWIPE_THRESHOLD = 80; // px

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

  const now = new Date();
  const createdAtDate = deal.created_at ? new Date(deal.created_at) : null;
  const ageHours = createdAtDate ? (now.getTime() - createdAtDate.getTime()) / (1000 * 60 * 60) : 999;
  const isWithin24h = ageHours < 24;
  const isExpiringSoon = deal.source === "community" && ageHours > 20;
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
    addRecent(deal.id);
    onClick?.(deal);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      handleCardClick();
    }
  };

  // 접근성용 카드 요약 레이블
  const ariaLabel = [
    deal.title,
    isFree ? "무료" : formatPrice(deal.sale_price),
    deal.discount_rate > 0 ? `${Math.round(deal.discount_rate)}% 할인` : null,
    deal.category,
  ].filter(Boolean).join(", ");

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return;
    const dx = e.touches[0].clientX - touchStartX.current;
    setSwipeX(dx);
  };

  const handleTouchEnd = () => {
    if (swipeX < -SWIPE_THRESHOLD) {
      // 왼쪽 스와이프 → dismiss
      setIsDismissing(true);
      setTimeout(() => onDismiss?.(deal.id), 300);
    } else if (swipeX > SWIPE_THRESHOLD) {
      // 오른쪽 스와이프 → 링크 열기
      const url = deal.affiliate_url || deal.product_url;
      if (url) window.open(url, "_blank", "noopener");
    }
    touchStartX.current = null;
    setSwipeX(0);
  };

  return (
    <div
      ref={cardRef}
      role="article"
      tabIndex={0}
      aria-label={ariaLabel}
      style={{
        transform: isDismissing
          ? "translateX(-110%)"
          : `translateX(${swipeX * 0.6}px)`, // 저항감 (0.6 damping)
        transition: swipeX === 0 || isDismissing ? "transform 0.3s ease" : "none",
        opacity: isDismissing ? 0 : 1,
      }}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onKeyDown={handleKeyDown}
      className="deal-card group relative cursor-pointer hover:shadow-xl hover:-translate-y-1 transition-all duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#E31E24]"
      onClick={handleCardClick}
    >
      {/* 왼쪽 스와이프 힌트 (빨간 X) */}
      {swipeX < -20 && (
        <div
          aria-hidden="true"
          className="absolute inset-0 flex items-center justify-end pr-4 rounded-lg bg-red-50 pointer-events-none z-10"
          style={{ opacity: Math.min(1, Math.abs(swipeX) / SWIPE_THRESHOLD) }}
        >
          <span className="text-2xl font-bold text-red-500">✕</span>
        </div>
      )}
      {/* 오른쪽 스와이프 힌트 (초록 링크) */}
      {swipeX > 20 && (
        <div
          aria-hidden="true"
          className="absolute inset-0 flex items-center justify-start pl-4 rounded-lg bg-green-50 pointer-events-none z-10"
          style={{ opacity: Math.min(1, swipeX / SWIPE_THRESHOLD) }}
        >
          <span className="text-2xl">🔗</span>
        </div>
      )}

      {/* 이미지 영역 */}
      <div className="relative overflow-hidden bg-gray-100 aspect-square">
        <FavoriteButton dealId={deal.id} />
        {deal.image_url && !imgError ? (
          <Image
            src={deal.image_url}
            alt={deal.title}
            fill
            sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 20vw"
            className="object-cover group-hover:scale-105 transition-transform duration-300"
            onError={() => setImgError(true)}
          />
        ) : (
          <div className={`w-full h-full flex flex-col items-center justify-center gap-1.5 bg-gradient-to-br ${CATEGORY_GRADIENT[deal.category] || "from-gray-50 to-gray-100"}`}>
            <span className="text-3xl">{CATEGORY_EMOJI[deal.category] || "📦"}</span>
            <span className="text-[10px] text-gray-400 font-medium">{deal.category}</span>
          </div>
        )}

        {/* 상단 배지 — 하나만 표시 */}
        {isFree ? (
          <div className="absolute top-0 left-0 bg-emerald-600 text-white text-[11px] font-bold px-2.5 py-1.5 leading-none tracking-wide">
            무료
          </div>
        ) : deal.status === "price_changed" ? (
          <div className="absolute top-0 left-0 bg-amber-500 text-white text-[11px] font-bold px-2.5 py-1.5 leading-none tracking-wide">
            가격변동
          </div>
        ) : deal.is_hot ? (
          <div className="absolute top-0 left-0 bg-[#E31E24] text-white text-[11px] font-bold px-2.5 py-1.5 leading-none tracking-wide">
            HOT딜
          </div>
        ) : deal.discount_rate > 0 ? (
          <div className="absolute top-0 left-0 bg-gradient-to-r from-red-500 to-orange-500 text-white text-[12px] font-black px-2.5 py-1.5 leading-none shadow-sm">
            -{Math.round(deal.discount_rate)}%
          </div>
        ) : deal.source === "community" ? (
          <div className="absolute top-0 left-0 bg-indigo-600 text-white text-[11px] font-bold px-2.5 py-1.5 leading-none">
            커뮤니티
          </div>
        ) : null}

        {/* 남은시간 배지 (24h 이내, is_hot 아닐 때만) / 마감임박 */}
        {(isWithin24h && !deal.is_hot) && (
          <div className="absolute top-0 right-0 leading-none">
            <TimeLeftBadge createdAt={deal.created_at} />
          </div>
        )}
        {isExpiringSoon && !deal.is_hot && (
          <div className={`absolute ${(isWithin24h && !deal.is_hot) ? "top-5" : "top-0"} right-0 bg-orange-500 text-white text-[9px] font-bold px-1.5 py-0.5 leading-none`}>
            마감임박
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
            <span className={`text-[10px] font-medium px-1.5 py-0.5 leading-tight ${
              deal.source === "watchlist" ? "bg-purple-600/80 text-white" :
              deal.source === "naver" ? "bg-green-600/80 text-white" :
              deal.source === "community" ? "bg-blue-600/80 text-white" :
              "bg-black/65 text-white"
            }`}>
              {deal.source === "naver" ? "네이버" : deal.source === "coupang" ? "쿠팡" : deal.source === "watchlist" ? "워치리스트" : "커뮤니티"}
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
        ) : deal.source === "community" && deal.discount_rate > 0 && deal.original_price > 0 ? (
          <p className="text-[11px] text-indigo-600 font-semibold mt-0.5">
            네이버 최저가 대비 -{Math.round(deal.discount_rate)}% ↓
          </p>
        ) : saved > 100 ? (
          <p className="text-[11px] text-emerald-600 font-semibold mt-0.5">
            {formatPrice(saved)} 절약 ↓
          </p>
        ) : null}

        {/* C-001 + C-009: 관심/클릭 배지 — today_views 있으면 우선 표시 */}
        {((deal.today_views ?? 0) >= 5 || (deal.total_clicks ?? 0) >= 100) && (
          <div className="flex flex-wrap gap-1 mt-1.5">
            {(deal.today_views ?? 0) >= 5 ? (
              <span className="text-[10px] font-semibold text-orange-600 bg-orange-50 border border-orange-100 px-1.5 py-0.5 leading-tight">
                👁 {deal.today_views}명 관심
              </span>
            ) : (deal.total_clicks ?? 0) >= 100 ? (
              <span className="text-[10px] font-semibold text-blue-600 bg-blue-50 border border-blue-100 px-1.5 py-0.5 leading-tight">
                🛒 {deal.total_clicks!.toLocaleString()}명 클릭
              </span>
            ) : null}
          </div>
        )}

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
            aria-label={`추천 ${upvotes}개${voted ? " (이미 추천함)" : " — 클릭하여 추천"}`}
            aria-pressed={voted}
            className={`flex items-center gap-1 text-[11px] font-medium transition-colors ${
              voted ? "text-gray-300" : "text-gray-500 hover:text-[#E31E24]"
            }`}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill={voted ? "#E31E24" : "none"} stroke="currentColor" strokeWidth="2" aria-hidden="true">
              <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3H14z" />
              <path d="M7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
            </svg>
            <span aria-hidden="true">{upvotes}</span>
          </button>
        </div>

        {/* C-015: 제휴마케팅 투명성 배지 */}
        {(deal.source === "coupang" ||
          (deal.affiliate_url && deal.affiliate_url.includes("coupang.com")) ||
          (deal.product_url && deal.product_url.includes("partners.coupang.com"))) && (
          <span className="text-xs text-gray-300">파트너스 광고</span>
        )}

        {/* 구매 링크 */}
        {targetUrl ? (
          <a
            href={targetUrl}
            target="_blank"
            rel="noopener noreferrer sponsored"
            onClick={(e) => { e.stopPropagation(); trackEvent("outbound_click", deal.id); }}
            className={`block mt-2 text-center text-[12px] font-bold py-2.5 transition-all active:scale-95 ${
              deal.is_hot || deal.discount_rate >= 40
                ? "bg-gradient-to-r from-red-500 to-orange-500 text-white hover:from-red-600 hover:to-orange-600 shadow-sm"
                : "border border-gray-200 text-gray-700 hover:border-gray-900 hover:text-black"
            }`}
          >
            {isFree ? "받기" : deal.source === "community" ? "보러가기" : "구매하기"}
          </a>
        ) : (
          <span
            onClick={(e) => e.stopPropagation()}
            className="block mt-2 text-center text-[12px] font-bold py-2.5 bg-gray-50 text-gray-300 cursor-default"
          >
            링크 없음
          </span>
        )}
      </div>
    </div>
  );
}
