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

interface TopDeal {
  id: string;
  title: string;
  sale_price: number | null;
  original_price: number | null;
  discount_rate: number | null;
  image_url: string | null;
  product_url: string | null;
  affiliate_url: string | null;
  source: string | null;
  category: string | null;
  status: string | null;
  submitter_name: string | null;
  created_at: string | null;
  is_hot: boolean | null;
}

async function getBrandTopDeals(slug: string): Promise<{ brand: string | null; deals: TopDeal[] }> {
  const res = await fetch(`${API_BASE}/api/brands/${slug}/top-deals`, { next: { revalidate: 600 } });
  if (!res.ok) return { brand: null, deals: [] };
  return res.json();
}

async function getBrandLowestEver(slug: string): Promise<TopDeal[]> {
  const res = await fetch(`${API_BASE}/api/brands/${slug}/lowest-ever`, { next: { revalidate: 600 } });
  if (!res.ok) return [];
  return res.json();
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
    keywords: `${brand} 최저가, ${brand} 할인, ${brand} 특가, ${brand} 세일`,
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
  const [dealsData, categories, topDealsResult, lowestDeals] = await Promise.all([
    getDeals({ page: 1, size: 40, sort: "discount", brand }),
    getCategories(),
    getBrandTopDeals(slug),
    getBrandLowestEver(slug),
  ]);
  const topDeals = topDealsResult.deals;

  const desc = BRAND_DESC[brand] || `${brand} 제품의 공식 정가 대비 현재 최저가를 실시간으로 추적합니다.`;

  // 활성 딜 중 최저 sale_price (역대 최저가 배지용)
  const activePrices = dealsData.items
    .map((d) => d.sale_price)
    .filter((p): p is number => typeof p === "number" && p > 0);
  const minActivePrice = activePrices.length > 0 ? Math.min(...activePrices) : null;

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

        {/* 역대 최저 등록가 TOP 5 */}
        {lowestDeals.length > 0 && (
          <section className="mb-8">
            <h2 className="text-base font-bold mb-3 text-gray-700">역대 최저 등록가</h2>
            <div className="space-y-2">
              {lowestDeals.map((d, i) => (
                <div key={d.id} className="flex items-center gap-3 py-2 border-b border-gray-100">
                  <span className="text-xs font-bold text-[#E31E24] w-5">#{i + 1}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate">{d.title}</p>
                    <p className="text-xs text-gray-400">
                      {d.created_at ? new Date(d.created_at).toLocaleDateString("ko-KR") : ""}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    {d.sale_price != null && (
                      <p className="text-sm font-bold">{d.sale_price.toLocaleString()}원</p>
                    )}
                    {d.discount_rate != null && (
                      <p className="text-xs text-[#E31E24]">-{d.discount_rate.toFixed(0)}%</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 현재 최저가 딜 하이라이트 */}
        {minActivePrice !== null && dealsData.items.length > 0 && (() => {
          const cheapest = dealsData.items.find((d) => d.sale_price === minActivePrice);
          if (!cheapest) return null;
          return (
            <div className="mb-6 flex items-center gap-3 bg-red-50 border border-red-100 px-4 py-3">
              <span className="bg-[#E31E24] text-white text-[10px] font-bold px-2 py-0.5 shrink-0">역대 최저</span>
              <p className="text-sm text-gray-800 truncate flex-1">{cheapest.title}</p>
              <span className="text-sm font-bold text-[#E31E24] shrink-0">{minActivePrice.toLocaleString()}원</span>
            </div>
          );
        })()}

        {/* 딜 그리드 */}
        {dealsData.items.length > 0 ? (
          <DealGrid deals={dealsData.items} />
        ) : (
          <div className="py-20 text-center text-gray-400">
            현재 {brand} 진행 중인 딜이 없습니다.
          </div>
        )}

        {/* 역대 최저가 TOP 10 */}
        {topDeals.length > 0 && (
          <div className="mt-12">
            <h2 className="text-lg font-bold text-gray-900 mb-4">🏆 역대 최저가 TOP 10</h2>
            <div className="rounded-xl border border-gray-100 overflow-hidden">
              <ol className="divide-y divide-gray-100">
                {topDeals.map((deal, idx) => {
                  const isActive = deal.status === "active" || deal.status === "price_changed";
                  const href = deal.affiliate_url || deal.product_url || "#";
                  const dateStr = deal.created_at
                    ? new Date(deal.created_at).toLocaleDateString("ko-KR", { year: "2-digit", month: "numeric", day: "numeric" })
                    : "";

                  const inner = (
                    <div className={`flex items-center gap-4 px-4 py-3 ${isActive ? "hover:bg-gray-50" : "opacity-50"}`}>
                      {/* 순위 */}
                      <span className={`w-6 text-center text-sm font-bold shrink-0 ${idx === 0 ? "text-yellow-500" : idx === 1 ? "text-gray-400" : idx === 2 ? "text-amber-700" : "text-gray-300"}`}>
                        {idx + 1}
                      </span>
                      {/* 제품명 */}
                      <span className="flex-1 text-sm text-gray-800 line-clamp-1 min-w-0">
                        {deal.title}
                      </span>
                      {/* 할인율 */}
                      {deal.discount_rate != null && (
                        <span className="text-sm font-bold text-[#E31E24] shrink-0">
                          -{Math.round(deal.discount_rate)}%
                        </span>
                      )}
                      {/* 금액 */}
                      {deal.sale_price != null && (
                        <span className="text-sm font-semibold text-gray-900 shrink-0 w-24 text-right">
                          {deal.sale_price.toLocaleString("ko-KR")}원
                        </span>
                      )}
                      {/* 날짜 */}
                      <span className="text-xs text-gray-400 shrink-0 w-16 text-right hidden sm:block">
                        {dateStr}
                      </span>
                      {/* 상태 뱃지 */}
                      {!isActive && (
                        <span className="text-xs text-gray-400 shrink-0">종료</span>
                      )}
                    </div>
                  );

                  return (
                    <li key={deal.id}>
                      {isActive && href !== "#" ? (
                        <a href={href} target="_blank" rel="noopener noreferrer" className="block">
                          {inner}
                        </a>
                      ) : (
                        inner
                      )}
                    </li>
                  );
                })}
              </ol>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
