import { Suspense } from "react";
import { Metadata } from "next";
import Link from "next/link";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";

// C-008: 공동구매 섹션

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

export const metadata: Metadata = {
  title: "공동구매 딜 | 정가파괴",
  description: "공동구매·공구 딜 모음 — 같이 사면 더 싸게!",
};

async function getGroupBuyDeals() {
  try {
    const url = `${API_BASE}/api/deals?search=${encodeURIComponent("공구")}&status=active&sort=latest&size=40`;
    const res = await fetch(url, { next: { revalidate: 30 } });
    if (!res.ok) return { items: [], total: 0 };
    return res.json();
  } catch {
    return { items: [], total: 0 };
  }
}

export default async function GroupBuyPage() {
  const dealsData = await getGroupBuyDeals();

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
          <span className="text-2xl">🛒</span>
          <h1 className="text-xl font-black text-gray-900">공동구매 딜</h1>
          {dealsData.total > 0 && (
            <span className="text-sm text-gray-400">
              {dealsData.total.toLocaleString()}개
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 ml-8">여럿이 함께 사면 더 싸요!</p>
      </div>

      {/* 딜 그리드 */}
      {dealsData.items.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-gray-300 text-5xl mb-4">🛒</p>
          <p className="text-gray-500 text-sm">
            현재 공동구매 딜이 없어요. 나중에 다시 확인해 보세요.
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
            filterParams={{ search: "공구", sort: "latest" }}
          />
        </Suspense>
      )}
    </div>
  );
}
