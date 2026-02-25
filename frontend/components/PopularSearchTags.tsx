"use client";

import { useRouter } from "next/navigation";

// C-002: 인기 검색어 태그 위젯 (쿠차 스타일)
interface PopularSearch {
  keyword: string;
  count: number;
}

interface PopularSearchTagsProps {
  searches: PopularSearch[];
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
        {searches.map((s, idx) => (
          <button
            key={s.keyword}
            onClick={() => handleClick(s.keyword)}
            className="flex items-center gap-1 text-[12px] font-medium px-2.5 py-1 bg-gray-50 border border-gray-200 text-gray-700 hover:border-gray-900 hover:text-black hover:bg-white transition-colors rounded-sm"
          >
            <span className="text-[10px] text-gray-400 font-bold">{idx + 1}</span>
            <span>#{s.keyword}</span>
            {s.count >= 3 && (
              <span className="text-[10px] text-gray-400">({s.count})</span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
