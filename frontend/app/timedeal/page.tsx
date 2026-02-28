import { Suspense } from "react";
import { Metadata } from "next";
import Link from "next/link";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";

// E-001: 타임딜/시간 오픈 딜 강조 섹션

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

export const metadata: Metadata = {
  title: "타임딜 · 한정수량 특가 | 정가파괴",
  description:
    "오늘만 특가·한정수량·시간 오픈 딜 모음 — 정가파괴. 놓치면 후회할 타임딜만 골랐습니다.",
};

async function getTimedealDeals() {
  try {
    const keywords = ["타임딜", "오늘만", "한정수량", "시간특가", "특가"];
    const results = await Promise.all(
      keywords.map((kw) =>
        fetch(
          `${API_BASE}/api/deals?search=${encodeURIComponent(kw)}&status=active&sort=hot&size=40`,
          { next: { revalidate: 20 } }
        ).then((res) => (res.ok ? res.json() : { items: [], total: 0 }))
      )
    );

    // id 기준 중복 제거, hot_score 내림차순 정렬
    const seen = new Set<number>();
    const merged: any[] = [];
    for (const data of results) {
      for (const item of data.items || []) {
        if (!seen.has(item.id)) {
          seen.add(item.id);
          merged.push(item);
        }
      }
    }
    merged.sort((a, b) => (b.hot_score ?? 0) - (a.hot_score ?? 0));

    return { items: merged, total: merged.length };
  } catch {
    return { items: [], total: 0 };
  }
}

export default async function TimedealPage() {
  const dealsData = await getTimedealDeals();

  return (
    <div className="max-w-screen-xl mx-auto px-4 py-6">
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
          <span className="text-2xl">⚡</span>
          <h1 className="text-xl font-black text-gray-900">타임딜 · 한정특가</h1>
          {dealsData.total > 0 && (
            <span className="text-sm text-gray-400">
              {dealsData.total.toLocaleString()}개
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 ml-8">
          오늘만 · 한정수량 · 시간 오픈 특가 — 놓치면 후회할 딜만 골랐어요
        </p>
      </div>

      {/* 딜 그리드 */}
      {dealsData.items.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-gray-300 text-5xl mb-4">⚡</p>
          <p className="text-gray-500 text-sm">
            현재 진행 중인 타임딜이 없어요.
          </p>
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
            initialDeals={dealsData.items}
            filterParams={{ search: "타임딜" }}
          />
        </Suspense>
      )}
    </div>
  );
}
