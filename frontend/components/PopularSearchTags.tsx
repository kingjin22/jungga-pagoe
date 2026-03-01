"use client";

import { useRouter } from "next/navigation";

// C-024: 인기 검색어 태그 위젯 — 쿠차 스타일 (키워드 + 할인율 + 최저가)
interface PopularSearch {
  keyword: string;
  count: number;
  discount_rate?: number | null;
  min_price?: number | null;
}

interface PopularSearchTagsProps {
  searches: PopularSearch[];
}

function formatPrice(price: number): string {
  return price.toLocaleString("ko-KR") + "원";
}

export default function PopularSearchTags({ searches }: PopularSearchTagsProps) {
  const router = useRouter();

  if (!searches || searches.length === 0) return null;

  const handleClick = (keyword: string) => {
    router.push(`/search?q=${encodeURIComponent(keyword)}`);
  };

  return (
    <div className="mb-4">
      <p className="text-[11px] text-gray-400 font-medium mb-2">🔥 인기 검색어</p>
      <div className="flex flex-wrap gap-1.5">
        {searches.map((s, idx) => {
          const hasDiscount = s.discount_rate != null && s.discount_rate > 0;
          const hasPrice = s.min_price != null && s.min_price > 0;
          const showMeta = hasDiscount || hasPrice;

          return (
            <button
              key={s.keyword}
              onClick={() => handleClick(s.keyword)}
              className="flex flex-col items-start gap-0.5 text-left px-2.5 py-1.5 bg-gray-50 border border-gray-200 hover:border-gray-900 hover:bg-white transition-colors rounded-sm min-w-0"
            >
              {/* 상단: 순위 + 키워드 */}
              <div className="flex items-center gap-1">
                <span className="text-[10px] text-gray-400 font-bold leading-none">{idx + 1}</span>
                <span className="text-[12px] font-semibold text-gray-700 leading-none">#{s.keyword}</span>
              </div>
              {/* 하단: 할인율 + 최저가 (있을 때만) */}
              {showMeta && (
                <div className="flex items-center gap-1 pl-[14px]">
                  {hasDiscount && (
                    <span className="text-[10px] font-bold text-red-500 leading-none">
                      {s.discount_rate}%
                    </span>
                  )}
                  {hasDiscount && hasPrice && (
                    <span className="text-[9px] text-gray-300 leading-none">·</span>
                  )}
                  {hasPrice && (
                    <span className="text-[10px] text-gray-400 leading-none">
                      {formatPrice(s.min_price!)}
                    </span>
                  )}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
