import { Metadata } from "next";
import ElectronicsClient from "./ElectronicsClient";

// E-003: 전자기기·PC·생활가전 전용 섹션 (RTX/갤럭시/노트북/생활가전)

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

export const metadata: Metadata = {
  title: "전자기기·PC·가전 최저가 | 정가파괴",
  description:
    "갤럭시·아이폰·RTX 그래픽카드·노트북·생활가전 최저가 할인 — 정가 대비 실제 할인 딜만. 정가파괴에서 지금 득템하세요.",
  keywords:
    "그래픽카드 최저가, RTX 할인, 노트북 특가, 갤럭시 할인, 아이폰 최저가, 생활가전 세일, 다이슨 할인",
  openGraph: {
    title: "전자기기·PC·가전 최저가 | 정가파괴",
    description:
      "RTX 그래픽카드·갤럭시·아이폰·노트북·생활가전 최저가 딜 모음",
    url: "https://jungga-pagoe.vercel.app/electronics",
  },
  alternates: {
    canonical: "https://jungga-pagoe.vercel.app/electronics",
  },
};

async function getElectronicsDeals() {
  try {
    // 전자기기 + 노트북/PC + 생활가전 카테고리 병렬 fetch
    const categories = ["전자기기", "노트북/PC", "생활가전"];
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

export default async function ElectronicsPage() {
  const dealsData = await getElectronicsDeals();

  // JSON-LD: BreadcrumbList + ItemList 스키마
  const jsonLd = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "정가파괴",
            item: "https://jungga-pagoe.vercel.app",
          },
          {
            "@type": "ListItem",
            position: 2,
            name: "전자기기·PC·가전",
            item: "https://jungga-pagoe.vercel.app/electronics",
          },
        ],
      },
      {
        "@type": "ItemList",
        name: "전자기기·PC·가전 최저가 딜",
        description:
          "갤럭시·아이폰·RTX 그래픽카드·노트북·생활가전 최저가 할인 딜 모음",
        numberOfItems: dealsData.total,
        itemListElement: dealsData.items.slice(0, 10).map((item: any, idx: number) => ({
          "@type": "ListItem",
          position: idx + 1,
          name: item.title,
          url: `https://jungga-pagoe.vercel.app/deal/${item.id}`,
        })),
      },
    ],
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <div className="max-w-screen-xl mx-auto px-4 py-6">
        <ElectronicsClient
          initialDeals={dealsData.items}
          total={dealsData.total}
        />
      </div>
    </>
  );
}
