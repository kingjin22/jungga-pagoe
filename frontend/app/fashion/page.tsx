import { Suspense } from "react";
import { Metadata } from "next";
import Link from "next/link";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";

// E-002: 신발·패션·스포츠 시즌 전용 페이지 (어미새 데일리슈 벤치마킹)
// 봄/신학기 시즌(3월~4월) 타이밍 특화

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

export const metadata: Metadata = {
  title: "신발·패션·스포츠 최저가 | 정가파괴",
  description:
    "나이키·아디다스·노스페이스 신발·패션·스포츠 최저가 할인 — 봄 시즌 특가 딜 모음. 정가파괴에서 지금 최저가로 득템하세요.",
  keywords:
    "신발 할인, 나이키 최저가, 아디다스 세일, 패션 특가, 스포츠 할인, 봄 패션, 운동화 할인",
  openGraph: {
    title: "신발·패션·스포츠 최저가 | 정가파괴",
    description: "봄 시즌 나이키·아디다스·노스페이스 최저가 특가 모음",
    url: "https://jungga-pagoe.vercel.app/fashion",
  },
  alternates: {
    canonical: "https://jungga-pagoe.vercel.app/fashion",
  },
};

async function getFashionDeals() {
  try {
    // 패션 + 신발 + 스포츠 카테고리 병렬 fetch
    const categories = ["패션", "신발", "스포츠"];
    const results = await Promise.all(
      categories.map((cat) =>
        fetch(
          `${API_BASE}/api/deals?category=${encodeURIComponent(cat)}&status=active&sort=hot&size=60`,
          { next: { revalidate: 60 } }
        ).then((res) => (res.ok ? res.json() : { items: [], total: 0 }))
      )
    );

    // id 기준 중복 제거, hot_score 내림차순 정렬
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
    merged.sort((a, b) => (b.hot_score ?? 0) - (a.hot_score ?? 0));

    return { items: merged, total: merged.length };
  } catch {
    return { items: [], total: 0 };
  }
}

export default async function FashionPage() {
  const dealsData = await getFashionDeals();

  // 카테고리별 개수 집계 (서브탭 표시용)
  const categoryCount = dealsData.items.reduce(
    (acc: Record<string, number>, item: any) => {
      const cat = item.category || "기타";
      acc[cat] = (acc[cat] || 0) + 1;
      return acc;
    },
    {}
  );

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
          <span className="text-2xl">👟</span>
          <h1 className="text-xl font-black text-gray-900">신발·패션·스포츠</h1>
          {dealsData.total > 0 && (
            <span className="text-sm text-gray-400">
              {dealsData.total.toLocaleString()}개
            </span>
          )}
        </div>
        <p className="text-sm text-gray-500 ml-8">
          나이키·아디다스·노스페이스 등 봄 시즌 최저가 딜 모음
        </p>

        {/* 카테고리 서브탭 */}
        {dealsData.total > 0 && (
          <div className="flex flex-wrap gap-2 mt-3 ml-8">
            {(["패션", "신발", "스포츠"] as const).map((cat) => {
              const cnt = categoryCount[cat] ?? 0;
              return cnt > 0 ? (
                <Link
                  key={cat}
                  href={`/category/${cat === "패션" ? "fashion" : cat === "신발" ? "sneakers" : "sports"}`}
                  className="inline-flex items-center gap-1 px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200 transition-colors"
                >
                  {cat === "패션" ? "👗" : cat === "신발" ? "👟" : "⚽"} {cat}{" "}
                  <span className="text-gray-400">{cnt}</span>
                </Link>
              ) : null;
            })}
          </div>
        )}
      </div>

      {/* 딜 그리드 */}
      {dealsData.items.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-gray-300 text-5xl mb-4">👟</p>
          <p className="text-gray-500 text-sm">현재 패션·신발 딜이 없어요.</p>
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
            filterParams={{ category: "패션" }}
          />
        </Suspense>
      )}
    </div>
  );
}
