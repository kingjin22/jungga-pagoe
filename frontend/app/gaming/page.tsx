import { Suspense } from "react";
import { Metadata } from "next";
import Link from "next/link";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";
import { Deal } from "@/lib/api";

// E-005: 게임·스팀·콘솔 전용 섹션 (게이밍 주변기기 포함)

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

export const metadata: Metadata = {
  title: "게임·스팀·콘솔 최저가 | 정가파괴",
  description:
    "스팀 게임 할인, PS5·Xbox·닌텐도 스위치 최저가, 게이밍 마우스·키보드·모니터 특가 딜 모음 — 정가파괴",
  keywords:
    "스팀 게임 할인, PS5 최저가, Xbox 특가, 닌텐도 스위치 할인, 게이밍 마우스 특가, 기계식 키보드 할인, 게이밍 모니터",
  alternates: {
    canonical: "https://jungga-pagoe.vercel.app/gaming",
  },
  openGraph: {
    url: "https://jungga-pagoe.vercel.app/gaming",
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

export default async function GamingPage() {
  // 게이밍 관련 키워드 병렬 fetch
  const [
    steam,
    steamEn,
    game,
    gaming,
    ps5,
    xbox,
    nintendo,
    gamingKr,
    plus,
  ] = await Promise.all([
    fetchDealsBySearch("스팀", 30),
    fetchDealsBySearch("steam", 30),
    fetchDealsBySearch("게임", 30),
    fetchDealsBySearch("gaming", 30),
    fetchDealsBySearch("PS5", 30),
    fetchDealsBySearch("Xbox", 30),
    fetchDealsBySearch("닌텐도", 30),
    fetchDealsBySearch("게이밍", 30),
    fetchDealsBySearch("플스", 30),
  ]);

  // id 기준 중복 제거 후 upvotes 내림차순 정렬
  const seenIds = new Set<number>();
  const combinedDeals: Deal[] = [];
  for (const deal of [
    ...steam,
    ...steamEn,
    ...game,
    ...gaming,
    ...ps5,
    ...xbox,
    ...nintendo,
    ...gamingKr,
    ...plus,
  ]) {
    if (!seenIds.has(deal.id)) {
      seenIds.add(deal.id);
      combinedDeals.push(deal);
    }
  }

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
          <span className="text-2xl">🎮</span>
          <h1 className="text-xl font-black text-gray-900">게임·스팀·콘솔 최저가</h1>
          {combinedDeals.length > 0 && (
            <span className="text-sm text-gray-400">
              {combinedDeals.length}개
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 ml-8">
          스팀 할인 · PS5/Xbox/닌텐도 · 게이밍 주변기기
        </p>
      </div>

      {/* 딜 그리드 */}
      {combinedDeals.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-gray-300 text-5xl mb-4">🎮</p>
          <p className="text-gray-500 text-sm">현재 게이밍 딜을 불러오는 중입니다.</p>
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
            filterParams={{ search: "게임", sort: "latest" }}
          />
        </Suspense>
      )}
    </div>
  );
}
