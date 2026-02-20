import { Suspense } from "react";
import { getDeals, getHotDeals, getCategories } from "@/lib/api";
import DealGrid from "@/components/DealGrid";
import HotBanner from "@/components/HotBanner";
import SortBar from "@/components/SortBar";
import StatsBar from "@/components/StatsBar";
import CategoryFilter from "@/components/CategoryFilter";
import { DealGridSkeleton } from "@/components/DealSkeleton";
import PageViewTracker from "@/components/PageViewTracker";
import AdBanner from "@/components/AdBanner";
import Link from "next/link";
import CoupangBanner from "@/components/CoupangBanner";

interface SearchParams {
  page?: string;
  sort?: string;
  category?: string;
  source?: string;
  search?: string;
  hot_only?: string;
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const page = Number(params.page) || 1;
  const isFiltered = !!(params.category || params.source || params.search || params.hot_only);

  const [dealsData, hotDeals, categories] = await Promise.all([
    getDeals({
      page,
      size: 20,
      sort: params.sort || "discount",
      category: params.category,
      source: params.source,
      search: params.search,
      hot_only: params.hot_only === "true",
    }).catch(() => ({ items: [], total: 0, page: 1, size: 20, pages: 1 })),
    isFiltered ? Promise.resolve([]) : getHotDeals().catch(() => []),
    getCategories().catch(() => []),
  ]);

  return (
    <>
      <PageViewTracker />
      {/* 통계 바 */}
      <Suspense fallback={null}>
        <StatsBar />
      </Suspense>

      {/* 핫딜 배너 */}
      {!isFiltered && hotDeals.length > 0 && (
        <HotBanner deals={hotDeals} />
      )}

      {/* 메인 딜 목록 */}
      <div className="max-w-screen-xl mx-auto px-4 py-8">

        {/* 필터/검색 헤더 */}
        {params.search && (
          <div className="flex items-center gap-3 mb-6">
            <h1 className="text-lg font-bold text-gray-900">
              "{params.search}" 검색결과
            </h1>
            <Link
              href="/"
              className="text-xs text-gray-400 hover:text-gray-600 underline underline-offset-2"
            >
              초기화
            </Link>
          </div>
        )}

        {params.category && (
          <div className="flex items-center gap-3 mb-6">
            <h1 className="text-lg font-bold text-gray-900">{params.category}</h1>
          </div>
        )}

        {/* 섹션 헤더 */}
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-black text-gray-900">
            {params.hot_only === "true" ? "HOT 딜" : isFiltered ? "검색 결과" : "전체 딜"}
          </h2>
        </div>

        {/* 카테고리 필터 — DB 기반 동적 */}
        <Suspense fallback={null}>
          <CategoryFilter categories={categories} />
        </Suspense>

        {/* 정렬 바 */}
        <Suspense fallback={null}>
          <SortBar total={dealsData.total} />
        </Suspense>

        {/* 딜 그리드 */}
        {dealsData.items.length === 0 ? (
          <div className="text-center py-24">
            <p className="text-gray-300 text-5xl mb-4">ø</p>
            <p className="text-gray-500 text-sm">해당하는 딜이 없습니다</p>
            <Link
              href="/"
              className="mt-4 inline-block text-sm text-gray-900 underline underline-offset-2"
            >
              전체 딜 보기
            </Link>
          </div>
        ) : (
          <>
          {/* 광고 배너 — HotBanner 아래, 딜 그리드 위 */}
          {process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID && (
            <AdBanner
              slot={process.env.NEXT_PUBLIC_ADSENSE_SLOT_TOP || ""}
              format="horizontal"
              className="my-4"
            />
          )}

          <Suspense fallback={<DealGridSkeleton count={20} />}>
            <DealGrid deals={dealsData.items} />
          </Suspense>
          </>
        )}

        {/* 쿠팡 파트너스 배너 */}
        <CoupangBanner />

        {/* 페이지네이션 */}
        {dealsData.pages > 1 && (
          <div className="flex justify-center items-center gap-1 mt-12">
            {page > 1 && (
              <Link
                href={`/?page=${page - 1}&sort=${params.sort || "latest"}`}
                className="px-3 py-2 text-sm border border-gray-200 text-gray-600 hover:border-gray-900 hover:text-gray-900 transition-colors"
              >
                ‹
              </Link>
            )}
            {Array.from({ length: Math.min(dealsData.pages, 7) }, (_, i) => {
              const p = i + 1;
              return (
                <Link
                  key={p}
                  href={`/?page=${p}&sort=${params.sort || "latest"}`}
                  className={`px-3 py-2 text-sm border transition-colors ${
                    p === page
                      ? "border-gray-900 bg-gray-900 text-white font-bold"
                      : "border-gray-200 text-gray-600 hover:border-gray-900 hover:text-gray-900"
                  }`}
                >
                  {p}
                </Link>
              );
            })}
            {page < dealsData.pages && (
              <Link
                href={`/?page=${page + 1}&sort=${params.sort || "latest"}`}
                className="px-3 py-2 text-sm border border-gray-200 text-gray-600 hover:border-gray-900 hover:text-gray-900 transition-colors"
              >
                ›
              </Link>
            )}
          </div>
        )}
      </div>
    </>
  );
}
