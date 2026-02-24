import { Suspense } from "react";
import { getDeals, getHotDeals, getCategories, getTrendingDeals } from "@/lib/api";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import HotBanner from "@/components/HotBanner";
import SortBar from "@/components/SortBar";
import StatsBar from "@/components/StatsBar";
import CategoryFilter from "@/components/CategoryFilter";
import PageViewTracker from "@/components/PageViewTracker";
import AdBanner from "@/components/AdBanner";
import Link from "next/link";
import CoupangBanner from "@/components/CoupangBanner";
import TrendingSection from "@/components/TrendingSection";
import PriceFilter from "@/components/PriceFilter";
import RecentDeals from "@/components/RecentDeals";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";

interface SearchParams {
  sort?: string;
  category?: string;
  source?: string;
  search?: string;
  hot_only?: string;
  price_min?: string;
  price_max?: string;
}

export default async function HomePage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const params = await searchParams;
  const priceMin = Number(params.price_min || 0);
  const priceMax = Number(params.price_max || 0);
  const isFiltered = !!(params.category || params.source || params.search || params.hot_only || priceMin || priceMax);

  const [dealsData, hotDeals, categories, trendingDeals] = await Promise.all([
    getDeals({
      page: 1,
      size: 20,
      sort: params.sort || "latest",
      category: params.category,
      source: params.source,
      search: params.search,
      hot_only: params.hot_only === "true",
      price_min: priceMin || undefined,
      price_max: priceMax || undefined,
    }).catch(() => ({ items: [], total: 0, page: 1, size: 20, pages: 1 })),
    isFiltered ? Promise.resolve([]) : getHotDeals().catch(() => []),
    getCategories().catch(() => []),
    isFiltered ? Promise.resolve([]) : getTrendingDeals().catch(() => []),
  ]);

  // ItemList 구조화 데이터 — Google 검색에 딜 목록 노출
  const itemListJsonLd = dealsData.items.length > 0 ? {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "정가파괴 핫딜 목록",
    description: "브랜드 공식 정가 대비 진짜 할인만 모은 핫딜",
    url: "https://jungga-pagoe.vercel.app",
    numberOfItems: dealsData.total,
    itemListElement: dealsData.items.slice(0, 10).map((deal: any, idx: number) => ({
      "@type": "ListItem",
      position: idx + 1,
      url: `https://jungga-pagoe.vercel.app/deal/${deal.id}`,
      name: deal.title,
    })),
  } : null;

  return (
    <>
      {itemListJsonLd && (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(itemListJsonLd) }} />
      )}
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
            {params.hot_only === "true" ? "HOT딜" : isFiltered ? "검색 결과" : "전체 딜"}
          </h2>
        </div>

        {/* 카테고리 필터 — DB 기반 동적 */}
        <Suspense fallback={null}>
          <CategoryFilter categories={categories} />
        </Suspense>

        {/* 가격대 필터 */}
        <Suspense fallback={null}>
          <PriceFilter />
        </Suspense>

        {/* 정렬 바 */}
        <Suspense fallback={null}>
          <SortBar total={dealsData.total} />
        </Suspense>

        {/* 지금 인기 TOP 3 */}
        {!isFiltered && <TrendingSection deals={trendingDeals} />}

        {/* 최근 본 딜 */}
        {!isFiltered && <RecentDeals />}

        {/* 딜 그리드 (무한 스크롤) */}
        {dealsData.items.length === 0 ? (
          <div className="text-center py-24">
            <p className="text-gray-300 text-5xl mb-4">ø</p>
            <p className="text-gray-500 text-sm">
              {params.search
                ? "검색 결과가 없습니다. 다른 키워드로 시도해보세요."
                : "해당하는 딜이 없습니다"}
            </p>
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

          <InfiniteDealsClient
            initialDeals={dealsData.items}
            filterParams={{
              category: params.category,
              source: params.source,
              search: params.search,
              sort: params.sort,
              hot_only: params.hot_only,
              price_min: params.price_min,
              price_max: params.price_max,
            }}
          />
          </>
        )}

        {/* 쿠팡 파트너스 배너 */}
        <CoupangBanner />
      </div>
    </>
  );
}
