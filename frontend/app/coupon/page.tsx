import { Suspense } from "react";
import { Metadata } from "next";
import Link from "next/link";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";
import { Deal } from "@/lib/api";

// C-016: 쿠폰/할인코드 전용 섹션

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

export const metadata: Metadata = {
  title: "쿠폰·할인코드 모음 | 정가파괴",
  description:
    "알리익스프레스·쿠팡·G마켓 쿠폰코드, 프로모션 할인코드를 한곳에서 — 정가파괴",
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

export default async function CouponPage() {
  // 여러 키워드로 병렬 fetch
  const [couponKr, discountCode, promotion, couponEn, codeEn] = await Promise.all([
    fetchDealsBySearch("쿠폰", 30),
    fetchDealsBySearch("할인코드", 20),
    fetchDealsBySearch("프로모션", 20),
    fetchDealsBySearch("coupon", 20),
    fetchDealsBySearch("code", 20),
  ]);

  // id 기준 중복 제거 후 합산
  const seenIds = new Set<number>();
  const combinedDeals: Deal[] = [];
  for (const deal of [
    ...couponKr,
    ...discountCode,
    ...promotion,
    ...couponEn,
    ...codeEn,
  ]) {
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
          <span className="text-2xl">🎫</span>
          <h1 className="text-xl font-black text-gray-900">쿠폰·할인코드</h1>
          {combinedDeals.length > 0 && (
            <span className="text-sm text-gray-400">
              {combinedDeals.length}개
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 ml-8">
          알리익스프레스·쿠팡·G마켓 프로모션 코드, 지금 바로 써보세요 🎫
        </p>
      </div>

      {/* 딜 그리드 */}
      {combinedDeals.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-gray-300 text-5xl mb-4">🎫</p>
          <p className="text-gray-500 text-sm">현재 쿠폰·할인코드 딜이 없어요.</p>
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
            filterParams={{ search: "쿠폰", sort: "latest" }}
          />
        </Suspense>
      )}
    </div>
  );
}
