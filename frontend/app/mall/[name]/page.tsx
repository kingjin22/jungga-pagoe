import { Suspense } from "react";
import { Metadata } from "next";
import Link from "next/link";
import MallTabs, { MallItem } from "@/components/MallTabs";
import InfiniteDealsClient from "@/components/InfiniteDealsClient";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";

// C-026: 쇼핑몰별 딜 필터 페이지 (쿠차 벤치마킹)

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

const MALL_LABELS: Record<string, string> = {
  coupang:   "쿠팡",
  naver:     "네이버",
  gmarket:   "G마켓",
  "11st":    "11번가",
  lotteon:   "롯데온",
  auction:   "옥션",
  gsshop:    "GS SHOP",
  cjonstyle: "CJ온스타일",
};

const MALL_ICONS: Record<string, string> = {
  coupang:   "🛍️",
  naver:     "🟢",
  gmarket:   "🏪",
  "11st":    "🔴",
  lotteon:   "🟤",
  auction:   "🔨",
  gsshop:    "🟣",
  cjonstyle: "📺",
};

interface PageProps {
  params: Promise<{ name: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { name } = await params;
  const label = MALL_LABELS[name] || name;
  return {
    title: `${label} 핫딜 | 정가파괴`,
    description: `${label}의 최신 할인 핫딜 모음. 정가 대비 최대 할인가를 확인하세요.`,
    openGraph: {
      title: `${label} 핫딜 | 정가파괴`,
      description: `${label}의 최신 할인 핫딜 모음`,
    },
  };
}

async function getMallDeals(name: string) {
  try {
    const url = `${API_BASE}/api/deals?mall=${encodeURIComponent(name)}&status=active&sort=latest&size=40`;
    const res = await fetch(url, { next: { revalidate: 30 } });
    if (!res.ok) return { items: [], total: 0, page: 1, size: 40, pages: 1 };
    return res.json();
  } catch {
    return { items: [], total: 0, page: 1, size: 40, pages: 1 };
  }
}

async function getMalls(): Promise<MallItem[]> {
  try {
    const res = await fetch(`${API_BASE}/api/deals/malls`, {
      next: { revalidate: 120 },
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

export default async function MallPage({ params }: PageProps) {
  const { name } = await params;
  const label = MALL_LABELS[name] || name;
  const icon = MALL_ICONS[name] || "🏬";

  const [dealsData, malls] = await Promise.all([
    getMallDeals(name),
    getMalls(),
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
        <h1 className="text-lg font-black text-gray-900">
          {icon} {label} 핫딜
        </h1>
        <span className="text-sm text-gray-400">
          {dealsData.total?.toLocaleString() || 0}개
        </span>
      </div>

      {/* 쇼핑몰 탭 */}
      <MallTabs activeMall={name} malls={malls} />

      {/* 딜 그리드 */}
      {dealsData.items.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-gray-300 text-5xl mb-4">ø</p>
          <p className="text-gray-500 text-sm">
            현재 {label} 딜이 없어요. 다른 쇼핑몰을 확인해보세요!
          </p>
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
            filterParams={{ mall: name, sort: "latest" }}
          />
        </Suspense>
      )}
    </div>
  );
}
