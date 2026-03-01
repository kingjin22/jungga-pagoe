import { Suspense } from "react";
import { Metadata } from "next";
import Link from "next/link";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";
import { Deal } from "@/lib/api";

// E-004: 해외직구·알리 전용 섹션 (알리 초이스데이 3/1~3/7 타이밍)

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

export const metadata: Metadata = {
  title: "해외직구·알리 최저가 | 정가파괴",
  description:
    "알리익스프레스·아마존·직배 해외직구 최저가 — 알리 초이스데이, 직구 특가 딜 모음. 정가파괴에서 지금 득템하세요.",
  keywords: "알리 최저가, 해외직구 할인, 직구 특가, 알리익스프레스 할인, 직배 딜, 아마존 직구",
  alternates: {
    canonical: "https://jungga-pagoe.vercel.app/overseas",
  },
  openGraph: {
    url: "https://jungga-pagoe.vercel.app/overseas",
  },
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

export default async function OverseasPage() {
  // 해외직구 관련 키워드 병렬 fetch
  const [ali, jikgu, jikbae, amazon, amazonEn, aliexpress] = await Promise.all([
    fetchDealsBySearch("알리", 30),
    fetchDealsBySearch("직구", 30),
    fetchDealsBySearch("직배", 30),
    fetchDealsBySearch("아마존", 30),
    fetchDealsBySearch("amazon", 30),
    fetchDealsBySearch("aliexpress", 30),
  ]);

  // id 기준 중복 제거 후 hot_score 내림차순 정렬
  const seenIds = new Set<number>();
  const combinedDeals: Deal[] = [];
  for (const deal of [
    ...ali,
    ...jikgu,
    ...jikbae,
    ...amazon,
    ...amazonEn,
    ...aliexpress,
  ]) {
    if (!seenIds.has(deal.id)) {
      seenIds.add(deal.id);
      combinedDeals.push(deal);
    }
  }

  // upvotes 내림차순 정렬 (hot_score 대용)
  combinedDeals.sort((a, b) => (b.upvotes ?? 0) - (a.upvotes ?? 0));

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
          <span className="text-2xl">🌍</span>
          <h1 className="text-xl font-black text-gray-900">해외직구·알리 최저가</h1>
          {combinedDeals.length > 0 && (
            <span className="text-sm text-gray-400">
              {combinedDeals.length}개
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 ml-8">
          알리 초이스데이 · 직구 특가 · 직배 딜 모음
        </p>
      </div>

      {/* 딜 그리드 */}
      {combinedDeals.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-gray-300 text-5xl mb-4">🌍</p>
          <p className="text-gray-500 text-sm">현재 해외직구 딜을 불러오는 중입니다.</p>
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
            filterParams={{ search: "알리", sort: "latest" }}
          />
        </Suspense>
      )}
    </div>
  );
}
