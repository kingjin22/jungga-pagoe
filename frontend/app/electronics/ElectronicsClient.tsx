"use client";

import { useState } from "react";
import { Suspense } from "react";
import Link from "next/link";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";
import { Deal } from "@/lib/api";

type CategoryFilter = null | "전자기기" | "노트북/PC" | "생활가전";

const TABS: { label: string; value: CategoryFilter }[] = [
  { label: "전체", value: null },
  { label: "전자기기 💻", value: "전자기기" },
  { label: "노트북·PC 🖥️", value: "노트북/PC" },
  { label: "생활가전 🔌", value: "생활가전" },
];

interface Props {
  initialDeals: Deal[];
  total: number;
}

export default function ElectronicsClient({ initialDeals, total }: Props) {
  const [selectedCat, setSelectedCat] = useState<CategoryFilter>(null);

  const filteredDeals =
    selectedCat === null
      ? initialDeals
      : initialDeals.filter((d) => d.category === selectedCat);

  const filteredTotal = selectedCat === null ? total : filteredDeals.length;

  return (
    <>
      {/* 페이지 헤더 */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <Link
            href="/"
            className="text-gray-400 hover:text-gray-600 text-sm"
            aria-label="홈으로"
          >
            ← 전체
          </Link>
          <span className="text-2xl">💻</span>
          <h1 className="text-xl font-black text-gray-900">전자기기·PC·가전</h1>
          {filteredTotal > 0 && (
            <span className="text-sm text-gray-400">
              {filteredTotal.toLocaleString()}개
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 ml-8">
          RTX·갤럭시·노트북·생활가전 최저가
        </p>

        {/* 서브탭 */}
        {total > 0 && (
          <div className="flex flex-wrap gap-2 mt-3 ml-8">
            {TABS.map((tab) => {
              const isActive = selectedCat === tab.value;
              const cnt =
                tab.value === null
                  ? total
                  : initialDeals.filter((d) => d.category === tab.value).length;
              return (
                <button
                  key={tab.label}
                  onClick={() => setSelectedCat(tab.value)}
                  className={`inline-flex items-center gap-1 px-3 py-1 text-xs rounded-full transition-colors ${
                    isActive
                      ? "bg-gray-900 text-white"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                  }`}
                >
                  {tab.label}
                  {cnt > 0 && (
                    <span className={isActive ? "text-gray-300" : "text-gray-400"}>
                      {cnt}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* 딜 그리드 */}
      {filteredDeals.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-gray-300 text-5xl mb-4">💻</p>
          <p className="text-gray-500 text-sm">현재 전자기기·PC·가전 딜이 없어요.</p>
          <Link
            href="/"
            className="mt-4 inline-block text-sm text-gray-900 underline underline-offset-2"
          >
            전체 딜 보기
          </Link>
        </div>
      ) : (
        <Suspense fallback={<DealGridSkeleton count={20} />}>
          <InfiniteDealsClient
            key={selectedCat ?? "all"}
            initialDeals={filteredDeals}
            filterParams={
              selectedCat
                ? { category: selectedCat, sort: "hot" }
                : { sort: "hot" }
            }
          />
        </Suspense>
      )}
    </>
  );
}
