import { Suspense } from "react";
import { Metadata } from "next";
import Link from "next/link";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";
import { Deal } from "@/lib/api";

// C-011: 기프티콘/상품권 섹션

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

export const metadata: Metadata = {
  title: "기프티콘·상품권 딜 | 정가파괴",
  description: "기프티콘·상품권·교환권 할인 딜 모음",
};

async function fetchDealsBySearch(search: string, size: number): Promise<Deal[]> {
  try {
    const url = `${API_BASE}/api/deals?search=${encodeURIComponent(search)}&status=active&sort=latest&size=${size}`;
    const res = await fetch(url, { next: { revalidate: 30 } });
    if (!res.ok) return [];
    const data = await res.json();
    return data.items ?? [];
  } catch {
    return [];
  }
}

export default async function GifticonPage() {
  // 두 키워드로 병렬 fetch
  const [gifticonDeals, sangpumkwonDeals] = await Promise.all([
    fetchDealsBySearch("기프티콘", 30),
    fetchDealsBySearch("상품권", 30),
  ]);

  // id 기준 중복 제거
  const seenIds = new Set<number>();
  const combinedDeals: Deal[] = [];
  for (const deal of [...gifticonDeals, ...sangpumkwonDeals]) {
    if (!seenIds.has(deal.id)) {
      seenIds.add(deal.id);
      combinedDeals.push(deal);
    }
  }

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
          <span className="text-2xl">🎁</span>
          <h1 className="text-xl font-black text-gray-900">기프티콘·상품권 딜</h1>
          {combinedDeals.length > 0 && (
            <span className="text-sm text-gray-400">
              {combinedDeals.length}개
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 ml-8">
          스타벅스·파리바게뜨·올리브영 교환권도 할인!
        </p>
      </div>

      {/* 딜 그리드 */}
      {combinedDeals.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-gray-300 text-5xl mb-4">🎁</p>
          <p className="text-gray-500 text-sm">현재 기프티콘 딜이 없어요.</p>
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
            initialDeals={combinedDeals}
            filterParams={{ search: "기프티콘", sort: "latest" }}
          />
        </Suspense>
      )}
    </div>
  );
}
