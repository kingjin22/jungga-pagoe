import { Suspense } from "react";
import { Metadata } from "next";
import Link from "next/link";
import SourceTabs, { SourceItem } from "@/components/SourceTabs";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";

// C-014: 소스(채널)별 딜 뷰 페이지

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

const SOURCE_LABELS: Record<string, string> = {
  naver: "네이버",
  clien: "클리앙",
  ruliweb: "루리웹",
  quasarzone: "퀘이사존",
  community: "커뮤니티",
  manual: "직접등록",
  coupang: "쿠팡",
  ppomppu: "뽐뿌",
};

interface PageProps {
  params: Promise<{ name: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { name } = await params;
  const label = SOURCE_LABELS[name] || name;
  return {
    title: `${label} 딜 | 정가파괴`,
    description: `${label}에서 수집한 최신 핫딜 모음`,
  };
}

async function getSourceDeals(name: string) {
  try {
    const url = `${API_BASE}/api/deals?source=${encodeURIComponent(name)}&status=active&sort=latest&size=40`;
    const res = await fetch(url, { next: { revalidate: 30 } });
    if (!res.ok) return { items: [], total: 0, page: 1, size: 40, pages: 1 };
    return res.json();
  } catch {
    return { items: [], total: 0, page: 1, size: 40, pages: 1 };
  }
}

async function getSources(): Promise<SourceItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/deals/sources`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function SourcePage({ params }: PageProps) {
  const { name } = await params;
  const label = SOURCE_LABELS[name] || name;

  const [dealsData, sources] = await Promise.all([
    getSourceDeals(name),
    getSources(),
  ]);

  return (
    <div className="max-w-screen-xl mx-auto px-4 py-6">
      {/* 페이지 헤더 */}
      <div className="flex items-center gap-3 mb-4">
        <Link
          href="/"
          className="text-gray-400 hover:text-gray-600 text-sm"
          aria-label="홈으로"
        >
          ← 전체
        </Link>
        <h1 className="text-lg font-black text-gray-900">{label} 딜</h1>
        <span className="text-sm text-gray-400">{dealsData.total?.toLocaleString() || 0}개</span>
      </div>

      {/* 소스 탭 (현재 탭 하이라이트) */}
      <SourceTabs activeSource={name} sources={sources} />

      {/* 딜 그리드 */}
      {dealsData.items.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-gray-300 text-5xl mb-4">ø</p>
          <p className="text-gray-500 text-sm">아직 딜이 없어요</p>
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
            filterParams={{ source: name, sort: "latest" }}
          />
        </Suspense>
      )}
    </div>
  );
}
