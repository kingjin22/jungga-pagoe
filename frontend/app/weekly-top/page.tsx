import { Metadata } from "next";
import Link from "next/link";
import { getWeeklyTopDeals } from "@/lib/api";
import DealCard from "@/components/DealCard";

const BASE_URL = "https://jungga-pagoe.vercel.app";

export const revalidate = 3600;

export const metadata: Metadata = {
  title: "이번 주 최고 할인 TOP 10 | 정가파괴",
  description: "정가파괴 이번 주 할인율 TOP 10. 최대 할인 딜만 엄선했습니다.",
  alternates: {
    canonical: `${BASE_URL}/weekly-top`,
  },
  openGraph: {
    title: "이번 주 최고 할인 TOP 10 🔥 | 정가파괴",
    description: "정가파괴 이번 주 할인율 TOP 10. 최대 할인 딜만 엄선했습니다.",
    url: `${BASE_URL}/weekly-top`,
    type: "website",
  },
};

export default async function WeeklyTopPage() {
  let deals: Awaited<ReturnType<typeof getWeeklyTopDeals>> = [];
  try {
    deals = await getWeeklyTopDeals();
  } catch {
    // 빈 목록으로 폴백
  }

  // JSON-LD ItemList 스키마
  const itemListJsonLd = {
    "@context": "https://schema.org",
    "@type": "ItemList",
    name: "이번 주 최고 할인 TOP 10",
    description: "정가파괴 이번 주 할인율 상위 10개 딜",
    url: `${BASE_URL}/weekly-top`,
    numberOfItems: deals.length,
    itemListElement: deals.map((deal, i) => ({
      "@type": "ListItem",
      position: i + 1,
      url: `${BASE_URL}/deal/${deal.id}`,
      name: deal.title,
    })),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(itemListJsonLd) }}
      />

      <div className="max-w-screen-xl mx-auto px-4 py-8">
        {/* 헤더 */}
        <div className="mb-8">
          <h1 className="text-2xl font-black text-gray-900 mb-1">
            이번 주 최고 할인 TOP 10 🔥
          </h1>
          <p className="text-sm text-gray-400">최근 7일 할인율 높은 딜 순</p>
        </div>

        {deals.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            <p className="text-4xl mb-4">📦</p>
            <p className="text-sm">이번 주 딜을 불러오는 중입니다.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {deals.map((deal, i) => (
              <div key={deal.id} className="relative">
                {/* 순위 뱃지 */}
                <div
                  className={`absolute top-2 left-2 z-10 w-6 h-6 flex items-center justify-center text-xs font-black text-white ${
                    i === 0
                      ? "bg-yellow-500"
                      : i === 1
                      ? "bg-gray-400"
                      : i === 2
                      ? "bg-amber-600"
                      : "bg-gray-700"
                  }`}
                >
                  {i + 1}
                </div>
                <Link href={`/deal/${deal.id}`}>
                  <DealCard deal={deal} />
                </Link>
              </div>
            ))}
          </div>
        )}

        <div className="mt-10 text-center">
          <Link
            href="/"
            className="inline-block text-sm text-gray-500 border border-gray-200 px-6 py-2.5 hover:border-gray-400 transition-colors"
          >
            ← 전체 딜 보기
          </Link>
        </div>
      </div>
    </>
  );
}
