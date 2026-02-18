import { Suspense } from "react";
import { getDeals, getHotDeals } from "@/lib/api";
import DealCard from "@/components/DealCard";
import HotBanner from "@/components/HotBanner";
import SortBar from "@/components/SortBar";
import StatsBar from "@/components/StatsBar";
import { DealSkeletonGrid } from "@/components/DealSkeleton";
import Link from "next/link";

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

  const [dealsData, hotDeals] = await Promise.all([
    getDeals({
      page,
      size: 20,
      sort: params.sort || "latest",
      category: params.category,
      source: params.source,
      search: params.search,
      hot_only: params.hot_only === "true",
    }),
    getHotDeals(),
  ]);

  const isFiltered = !!(params.category || params.source || params.search || params.hot_only);

  return (
    <div>
      {/* 통계 바 */}
      <Suspense fallback={null}>
        <StatsBar />
      </Suspense>

      {/* 핫딜 배너 (필터 없을 때만) */}
      {!isFiltered && hotDeals.length > 0 && (
        <HotBanner deals={hotDeals} />
      )}

      {/* 검색 결과 헤더 */}
      {params.search && (
        <div className="mb-4 flex items-center gap-2">
          <span className="text-lg font-bold">"{params.search}" 검색 결과</span>
          <Link href="/" className="text-sm text-gray-400 hover:text-gray-600">
            ✕ 초기화
          </Link>
        </div>
      )}

      {/* 정렬 바 */}
      <Suspense fallback={null}>
        <SortBar total={dealsData.total} />
      </Suspense>

      {/* 딜 그리드 */}
      <Suspense fallback={<DealSkeletonGrid count={10} />}>
        {dealsData.items.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            <div className="text-5xl mb-4">😢</div>
            <p className="text-lg">해당하는 딜이 없어요</p>
            <Link href="/" className="mt-4 inline-block text-[#E31E24] hover:underline">
              전체 딜 보기
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {dealsData.items.map((deal) => (
              <DealCard key={deal.id} deal={deal} />
            ))}
          </div>
        )}
      </Suspense>

      {/* 페이지네이션 */}
      {dealsData.pages > 1 && (
        <div className="flex justify-center gap-2 mt-8">
          {page > 1 && (
            <Link
              href={`/?page=${page - 1}&sort=${params.sort || "latest"}`}
              className="px-4 py-2 bg-white border rounded-lg text-sm hover:bg-gray-50"
            >
              ← 이전
            </Link>
          )}
          {Array.from({ length: Math.min(dealsData.pages, 5) }, (_, i) => {
            const p = i + 1;
            return (
              <Link
                key={p}
                href={`/?page=${p}&sort=${params.sort || "latest"}`}
                className={`px-4 py-2 rounded-lg text-sm ${
                  p === page
                    ? "bg-[#E31E24] text-white font-bold"
                    : "bg-white border hover:bg-gray-50"
                }`}
              >
                {p}
              </Link>
            );
          })}
          {page < dealsData.pages && (
            <Link
              href={`/?page=${page + 1}&sort=${params.sort || "latest"}`}
              className="px-4 py-2 bg-white border rounded-lg text-sm hover:bg-gray-50"
            >
              다음 →
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
