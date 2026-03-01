import { Suspense } from "react";
import { getDeals, getHotDeals, getCategories, getTrendingDeals, getPopularSearches } from "@/lib/api";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import HotBanner from "@/components/HotBanner";
import SortBar from "@/components/SortBar";
import StickyFilter from "@/components/StickyFilter";
import PageViewTracker from "@/components/PageViewTracker";
import AdBanner from "@/components/AdBanner";
import Link from "next/link";
import CoupangBanner from "@/components/CoupangBanner";
import TrendingSection from "@/components/TrendingSection";
import PriceFilter from "@/components/PriceFilter";
import RecentDeals from "@/components/RecentDeals";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";
import PopularSearchTags from "@/components/PopularSearchTags";
import SeasonBanner from "@/components/SeasonBanner";
import SourceTabs from "@/components/SourceTabs";
import MallTabs from "@/components/MallTabs";

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

  const [dealsData, hotDeals, categories, trendingDeals, popularSearches] = await Promise.all([
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
    getPopularSearches().catch(() => []),
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

      {/* 히어로 배너 — 필터 없을 때만 */}
      {!isFiltered && (
        <div className="bg-gradient-to-r from-red-600 to-orange-500 text-white">
          <div className="max-w-screen-xl mx-auto px-4 py-5 flex items-center justify-between">
            <div>
              <h1 className="text-lg font-black tracking-tight">오늘도 쏟아지는 진짜 핫딜</h1>
              <p className="text-sm text-red-100 mt-0.5">정가 대비 진짜 할인, 직접 검증해요</p>
            </div>
            <Link
              href="/?hot_only=true"
              className="hidden sm:block bg-white text-red-600 text-sm font-bold px-4 py-2 rounded-full hover:bg-red-50 transition-colors whitespace-nowrap"
            >
              HOT딜 보기
            </Link>
          </div>
        </div>
      )}

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

        {/* 카테고리 필터 — 스티키 */}
        <Suspense fallback={null}>
          <StickyFilter categories={categories} />
        </Suspense>

        {/* 가격대 필터 */}
        <Suspense fallback={null}>
          <PriceFilter />
        </Suspense>

        {/* 정렬 바 */}
        <Suspense fallback={null}>
          <SortBar total={dealsData.total} />
        </Suspense>

        {/* C-002: 인기 검색어 태그 위젯 — 항상 표시 */}
        {popularSearches.length > 0 && (
          <PopularSearchTags searches={popularSearches} />
        )}

        {/* C-013: 시즌 특화 큐레이션 배너 */}
        {!isFiltered && <SeasonBanner />}

        {/* C-014: 소스별 채널 탭 필터 (알구몬식) — 전체 탭이 기본 선택 */}
        <SourceTabs activeSource={params.source} />

        {/* C-026: 쇼핑몰별 실시간 핫딜 탭 (쿠차 벤치마킹) */}
        {!isFiltered && <MallTabs />}

        {/* 지금 인기 TOP 3 */}
        {!isFiltered && <TrendingSection deals={trendingDeals} />}

        {/* 최근 본 딜 */}
        {!isFiltered && <RecentDeals />}

        {/* 딜 그리드 (무한 스크롤) */}
        {dealsData.items.length === 0 ? (
          <div className="text-center py-24">
            <p className="text-5xl mb-4">🤔</p>
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

          <Suspense fallback={<DealGridSkeleton count={20} />}>
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
          </Suspense>
          </>
        )}

        {/* 쿠팡 파트너스 배너 */}
        <CoupangBanner />
      </div>
    </>
  );
}
