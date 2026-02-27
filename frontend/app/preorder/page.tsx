import { Suspense } from "react";
import { Metadata } from "next";
import Link from "next/link";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";

// C-017: 신제품 사전구매 섹션

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

export const metadata: Metadata = {
  title: "신제품 사전구매 | 정가파괴",
  description:
    "갤럭시·아이폰·신형 노트북 사전예약 딜 모음 — 정가파괴",
};

async function getPreorderDeals() {
  try {
    const keywords = ["사전구매", "예약구매", "선주문", "사전예약", "pre-order"];
    const results = await Promise.all(
      keywords.map((kw) =>
        fetch(
          `${API_BASE}/api/deals?search=${encodeURIComponent(kw)}&status=active&sort=latest&size=30`,
          { next: { revalidate: 30 } }
        ).then((res) => (res.ok ? res.json() : { items: [], total: 0 }))
      )
    );

    // id 기준 중복 제거
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

    return { items: merged, total: merged.length };
  } catch {
    return { items: [], total: 0 };
  }
}

export default async function PreorderPage() {
  const dealsData = await getPreorderDeals();

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
          <span className="text-2xl">🚀</span>
          <h1 className="text-xl font-black text-gray-900">신제품 사전구매</h1>
          {dealsData.total > 0 && (
            <span className="text-sm text-gray-400">
              {dealsData.total.toLocaleString()}개
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 ml-8">갤럭시·아이폰·신형 노트북 사전예약 딜도 여기서</p>
      </div>

      {/* 딜 그리드 */}
      {dealsData.items.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-gray-300 text-5xl mb-4">🚀</p>
          <p className="text-gray-500 text-sm">
            현재 사전구매 딜이 없어요.
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
            filterParams={{ search: "사전구매" }}
          />
        </Suspense>
      )}
    </div>
  );
}
