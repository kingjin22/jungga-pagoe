import { Metadata } from "next";
import { getDeals, getCategories } from "@/lib/api";
import DealGrid from "@/components/DealGrid";
import CategoryFilter from "@/components/CategoryFilter";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// 슬러그 → 브랜드명 변환
async function getBrands(): Promise<{ brand: string; slug: string; count: number; avg_discount: number }[]> {
  const res = await fetch(`${API_BASE}/api/brands`, { next: { revalidate: 300 } });
  if (!res.ok) return [];
  return res.json();
}

async function getBrandBySlug(slug: string) {
  const brands = await getBrands();
  return brands.find((b) => b.slug === slug) || null;
}

// 브랜드 설명 (SEO용 텍스트)
const BRAND_DESC: Record<string, string> = {
  Apple: "아이폰, 맥북, 아이패드, 에어팟 등 Apple 정품의 최저가를 실시간으로 추적합니다. 공식 정가 대비 할인율을 투명하게 제공합니다.",
  Samsung: "갤럭시 스마트폰, 버즈, 워치, 탭 등 삼성 전자제품의 현재 최저가와 가격 히스토리를 확인하세요.",
  Nike: "나이키 운동화, 러닝화, 의류의 최저가 알림. 에어맥스, 페가수스, 에어포스1 할인 정보를 모아드립니다.",
  "New Balance": "뉴발란스 530, 993, 1906R 등 인기 스니커즈와 러닝화의 국내 최저가를 추적합니다.",
  Hoka: "호카 클리프톤, 본다이 등 러닝화의 최저가. 러너들을 위한 실시간 가격 정보.",
  Dyson: "다이슨 에어랩, V15, 슈퍼소닉 등 프리미엄 가전의 실제 할인가를 공식 정가와 비교합니다.",
  Sony: "소니 WH-1000XM5, WF-1000XM5 등 헤드폰/이어폰의 현재 최저가와 가격 추이를 제공합니다.",
  Salomon: "살로몬 스피드크로스, 트레일화의 최저가를 실시간으로 추적합니다.",
  "The North Face": "노스페이스 눕시 패딩, 자켓 등 아웃도어 의류의 할인 정보를 한곳에서 확인하세요.",
  Patagonia: "파타고니아 다운재킷, 플리스 등 프리미엄 아웃도어 브랜드의 실제 할인 정보.",
};

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const brandInfo = await getBrandBySlug(slug);
  if (!brandInfo) return { title: "브랜드 없음 | 정가파괴" };

  const { brand, count } = brandInfo;
  return {
    title: `${brand} 최저가 할인 모음 | 정가파괴`,
    description: `${brand} 공식 정가 대비 최저가 ${count}개 딜. ${BRAND_DESC[brand] || `${brand} 제품의 최저가를 실시간으로 추적합니다.`}`,
    openGraph: {
      title: `${brand} 최저가 | 정가파괴`,
      description: `${brand} 현재 할인 딜 ${count}개`,
    },
  };
}

export default async function BrandPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const brandInfo = await getBrandBySlug(slug);
  if (!brandInfo) {
    return (
      <div className="max-w-screen-xl mx-auto px-4 py-20 text-center text-gray-400">
        브랜드를 찾을 수 없습니다.
      </div>
    );
  }

  const { brand, count } = brandInfo;
  const [dealsData, categories] = await Promise.all([
    getDeals({ page: 1, size: 40, sort: "discount", brand }),
    getCategories(),
  ]);

  const desc = BRAND_DESC[brand] || `${brand} 제품의 공식 정가 대비 현재 최저가를 실시간으로 추적합니다.`;

  // Schema.org JSON-LD
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: `${brand} 최저가 할인 모음`,
    description: desc,
    url: `https://jungga-pagoe.vercel.app/brand/${slug}`,
  };

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="max-w-screen-xl mx-auto px-4 pt-8 pb-16">
        {/* 브랜드 헤더 */}
        <div className="mb-8 border-b border-gray-100 pb-6">
          <div className="flex items-baseline gap-3 mb-2">
            <h1 className="text-2xl font-bold text-gray-900">{brand}</h1>
            <span className="text-sm text-gray-400">현재 딜 {count}개</span>
            {brandInfo.avg_discount > 0 && (
              <span className="text-sm font-bold text-[#E31E24]">
                평균 -{brandInfo.avg_discount}%
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 leading-relaxed max-w-2xl">{desc}</p>
        </div>

        {/* 카테고리 필터 */}
        <div className="mb-6">
          <CategoryFilter categories={categories} />
        </div>

        {/* 딜 그리드 */}
        {dealsData.items.length > 0 ? (
          <DealGrid deals={dealsData.items} />
        ) : (
          <div className="py-20 text-center text-gray-400">
            현재 {brand} 진행 중인 딜이 없습니다.
          </div>
        )}
      </div>
    </>
  );
}
