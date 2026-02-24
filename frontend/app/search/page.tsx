import { Suspense } from "react";
import DealCard from "@/components/DealCard";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";

async function searchDeals(q: string) {
  if (!q) return [];
  const res = await fetch(`${API_BASE}/api/deals?search=${encodeURIComponent(q)}&size=40&sort=latest`, {
    next: { revalidate: 300 }
  });
  if (!res.ok) return [];
  const data = await res.json();
  return data.items ?? [];
}

export async function generateMetadata({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const params = await searchParams;
  const q = params.q || "";
  return {
    title: q ? `"${q}" 검색 결과 | 정가파괴` : "검색 | 정가파괴",
    description: q ? `"${q}" 관련 핫딜 정가 대비 최저가 모음` : "핫딜 검색",
  };
}

async function SearchResults({ q }: { q: string }) {
  const deals = await searchDeals(q);
  if (!q) return (
    <div className="py-20 text-center text-gray-400">
      <p className="text-2xl mb-2">🔍</p>
      <p>검색어를 입력하세요</p>
    </div>
  );
  return (
    <>
      <p className="text-sm text-gray-500 mb-4">
        <strong className="text-gray-900">"{q}"</strong> 검색 결과 {deals.length}개
      </p>
      {deals.length === 0 ? (
        <div className="py-20 text-center text-gray-400">
          <p className="text-2xl mb-2">😢</p>
          <p>검색 결과가 없습니다</p>
          <Link href="/" className="mt-4 inline-block text-sm text-blue-600 underline">전체 딜 보기</Link>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-x-4 gap-y-8">
          {deals.map((deal: any) => <DealCard key={deal.id} deal={deal} />)}
        </div>
      )}
    </>
  );
}

export default async function SearchPage({ searchParams }: { searchParams: Promise<{ q?: string }> }) {
  const params = await searchParams;
  const q = params.q || "";
  return (
    <div className="max-w-screen-xl mx-auto px-4 py-8">
      <h1 className="text-xl font-bold mb-6">검색</h1>
      <Suspense fallback={<p className="text-gray-400 text-sm">검색 중...</p>}>
        <SearchResults q={q} />
      </Suspense>
    </div>
  );
}
