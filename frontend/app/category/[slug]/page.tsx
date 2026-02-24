import { Metadata } from "next";
import { Suspense } from "react";
import { getDeals, getCategories } from "@/lib/api";
import { CATEGORIES, getCategoryBySlug } from "@/lib/categories";
import DealGrid from "@/components/DealGrid";
import CategoryFilter from "@/components/CategoryFilter";
import Link from "next/link";

export function generateStaticParams() {
  return Object.values(CATEGORIES).map((c) => ({ slug: c.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const cat = getCategoryBySlug(slug);
  if (!cat) return { title: "카테고리 없음 | 정가파괴" };

  return {
    title: `${cat.name} 최저가 할인 딜 | 정가파괴`,
    description: cat.desc,
    keywords: cat.keywords,
    openGraph: {
      title: `${cat.name} 최저가 | 정가파괴`,
      description: cat.desc,
      url: `https://jungga-pagoe.vercel.app/category/${cat.slug}`,
    },
    alternates: {
      canonical: `https://jungga-pagoe.vercel.app/category/${cat.slug}`,
    },
  };
}

export default async function CategoryPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const cat = getCategoryBySlug(slug);

  if (!cat) {
    return (
      <div className="max-w-screen-xl mx-auto px-4 py-20 text-center text-gray-400">
        카테고리를 찾을 수 없습니다.
      </div>
    );
  }

  const [dealsData, categories] = await Promise.all([
    getDeals({ page: 1, size: 20, sort: "latest", category: cat.name }),
    getCategories(),
  ]);

  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: `${cat.name} 최저가 할인 딜`,
    description: cat.desc,
    url: `https://jungga-pagoe.vercel.app/category/${cat.slug}`,
    ...(dealsData.items.length > 0 && {
      numberOfItems: dealsData.total,
      itemListElement: dealsData.items.slice(0, 10).map((deal, idx) => ({
        "@type": "ListItem",
        position: idx + 1,
        url: `https://jungga-pagoe.vercel.app/deal/${deal.id}`,
        name: deal.title,
      })),
    }),
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="max-w-screen-xl mx-auto px-4 pt-8 pb-16">
        {/* 카테고리 헤더 */}
        <div className="mb-8 border-b border-gray-100 pb-6">
          <div className="flex items-baseline gap-3 mb-2">
            <h1 className="text-2xl font-bold text-gray-900">
              {cat.name} 최저가 할인 딜
            </h1>
            <span className="text-sm text-gray-400">현재 딜 {dealsData.total}개</span>
          </div>
          <p className="text-sm text-gray-500 leading-relaxed max-w-2xl">{cat.desc}</p>
        </div>

        {/* 카테고리 필터 */}
        <div className="mb-6">
          <Suspense fallback={null}>
            <CategoryFilter categories={categories} />
          </Suspense>
        </div>

        {/* 딜 그리드 */}
        {dealsData.items.length > 0 ? (
          <DealGrid deals={dealsData.items} />
        ) : (
          <div className="py-20 text-center text-gray-400">
            <p className="text-4xl mb-4">ø</p>
            <p className="text-sm">현재 {cat.name} 진행 중인 딜이 없습니다.</p>
            <Link
              href="/"
              className="mt-4 inline-block text-sm text-gray-900 underline underline-offset-2"
            >
              전체 딜 보기
            </Link>
          </div>
        )}
      </div>
    </>
  );
}
