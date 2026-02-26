"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

// C-014: 알구몬식 소스별 채널 탭 필터

export interface SourceItem {
  source: string;
  label: string;
  count: number;
}

interface SourceTabsProps {
  activeSource?: string; // 현재 선택된 소스 (없으면 "전체")
  sources?: SourceItem[]; // 외부에서 주입 (SSR 용)
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

// 탭으로 노출할 소스 목록 (우선순위 순)
const TAB_ORDER = ["clien", "ruliweb", "quasarzone", "naver", "coupang", "ppomppu", "community"];

const SOURCE_LABELS: Record<string, string> = {
  naver: "네이버",
  clien: "클리앙",
  ruliweb: "루리웹",
  quasarzone: "퀘이사존",
  community: "커뮤니티",
  manual: "직접등록",
  coupang: "쿠팡",
  ppomppu: "뽐뿌",
};

export default function SourceTabs({ activeSource, sources: propSources }: SourceTabsProps) {
  const router = useRouter();
  const [sources, setSources] = useState<SourceItem[]>(propSources || []);

  useEffect(() => {
    if (propSources && propSources.length > 0) return; // SSR 데이터 있으면 fetch 생략
    fetch(`${API_BASE}/api/deals/sources`)
      .then((r) => r.json())
      .then((data: SourceItem[]) => setSources(data))
      .catch(() => {});
  }, [propSources]);

  // 개수 맵 생성
  const countMap: Record<string, number> = {};
  let totalCount = 0;
  for (const s of sources) {
    countMap[s.source] = s.count;
    totalCount += s.count;
  }

  // 실제로 데이터 있는 소스만 탭 표시 (TAB_ORDER 기준 정렬)
  const visibleSources = TAB_ORDER.filter((src) => countMap[src] != null);

  const handleClick = (source: string | null) => {
    if (source === null) {
      router.push("/");
    } else {
      router.push(`/source/${source}`);
    }
  };

  const isActive = (source: string | null) => {
    if (source === null) return !activeSource;
    return activeSource === source;
  };

  const tabBase =
    "flex-shrink-0 flex items-center gap-1.5 px-3 py-2 text-sm whitespace-nowrap transition-all border-b-2 cursor-pointer select-none";
  const tabActive = "font-bold text-blue-600 border-blue-500";
  const tabInactive = "font-medium text-gray-500 border-transparent hover:text-gray-800 hover:border-gray-300";

  return (
    <div className="w-full overflow-x-auto scrollbar-none mb-4">
      <div className="flex items-end gap-0 border-b border-gray-200 min-w-max">
        {/* 전체 탭 */}
        <button
          onClick={() => handleClick(null)}
          className={`${tabBase} ${isActive(null) ? tabActive : tabInactive}`}
          aria-current={isActive(null) ? "page" : undefined}
        >
          <span>전체</span>
          {totalCount > 0 && (
            <span
              className={`text-[11px] px-1.5 py-0.5 rounded-full ${
                isActive(null)
                  ? "bg-blue-100 text-blue-600"
                  : "bg-gray-100 text-gray-500"
              }`}
            >
              {totalCount.toLocaleString()}
            </span>
          )}
        </button>

        {/* 소스별 탭 */}
        {visibleSources.map((src) => {
          const label = SOURCE_LABELS[src] || src;
          const count = countMap[src] || 0;
          const active = isActive(src);
          return (
            <button
              key={src}
              onClick={() => handleClick(src)}
              className={`${tabBase} ${active ? tabActive : tabInactive}`}
              aria-current={active ? "page" : undefined}
            >
              <span>{label}</span>
              {count > 0 && (
                <span
                  className={`text-[11px] px-1.5 py-0.5 rounded-full ${
                    active
                      ? "bg-blue-100 text-blue-600"
                      : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {count.toLocaleString()}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
