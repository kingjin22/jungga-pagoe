import { Metadata } from "next";
import { notFound } from "next/navigation";
import Image from "next/image";
import Link from "next/link";
import { getDeal, getRelatedDeals, formatPrice } from "@/lib/api";
import PriceChart from "@/components/PriceChart";
import PriceHistoryChart from "@/components/PriceHistoryChart";
import DealCard from "@/components/DealCard";
import ShareButtons from "@/components/ShareButtons";

const BASE_URL = "https://jungga-pagoe.vercel.app";

function extractRetailer(title: string): string {
  const m = title.match(/^\[([^\]]{1,20})\]/);
  return m ? m[1] : "";
}

function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  try {
    const deal = await getDeal(Number(id));
    const dr = Math.round(deal.discount_rate);
    const price = formatPrice(deal.sale_price);
    const title = deal.title.replace(/^\[[^\]]+\]\s*/, ""); // [브랜드] 제거

    return {
      title: `${title} ${price} ${dr > 0 ? `-${dr}%` : ""} | 정가파괴`,
      description: `${deal.title} 현재 ${price}${dr > 0 ? ` (${dr}% 할인)` : ""}. 공식 정가 대비 최저가 확인 및 가격 히스토리 제공.`,
      openGraph: {
        title: `${title} ${price}${dr > 0 ? ` -${dr}%` : ""}`,
        description: `정가파괴 | ${deal.category} 최저가`,
        images: deal.image_url ? [{ url: deal.image_url }] : [],
        type: "website",
      },
      alternates: {
        canonical: `${BASE_URL}/deal/${id}`,
      },
    };
  } catch {
    return { title: "딜 없음 | 정가파괴" };
  }
}

export default async function DealPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let deal: any;
  try {
    deal = await getDeal(Number(id));
  } catch {
    notFound();
  }

  const relatedDeals = await getRelatedDeals(Number(id));

  if (!deal || deal.status === "expired") notFound();

  const saved = deal.original_price - deal.sale_price;
  const dr = Math.round(deal.discount_rate);
  const targetUrl = deal.affiliate_url || deal.product_url;
  const isFree = deal.sale_price === 0;
  const retailer = extractRetailer(deal.title);
  const brandSlug = slugify(deal.submitter_name || retailer || "");
  const cleanTitle = deal.title.replace(/^\[[^\]]+\]\s*/, "");

  const priceValidUntil = new Date(Date.now() + 86400000 * 3).toISOString().split("T")[0];

  // Product 스키마 — Google Shopping 리치 결과용
  const productJsonLd = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: cleanTitle,
    image: deal.image_url ? [deal.image_url] : undefined,
    description: `${cleanTitle} 최저가 ${formatPrice(deal.sale_price)}${dr > 0 ? ` (정가 ${formatPrice(deal.original_price)} 대비 ${dr}% 할인)` : ""}. 정가파괴에서 가격 히스토리를 확인하세요.`,
    ...(retailer && {
      brand: { "@type": "Brand", name: retailer },
    }),
    category: deal.category,
    offers: {
      "@type": "Offer",
      price: deal.sale_price,
      priceCurrency: "KRW",
      availability: "https://schema.org/InStock",
      url: `${BASE_URL}/deal/${id}`,
      priceValidUntil,
      seller: { "@type": "Organization", name: retailer || "온라인 쇼핑몰" },
    },
  };

  // BreadcrumbList 스키마 — 검색결과에 경로 표시
  const breadcrumbJsonLd = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "홈", item: BASE_URL },
      { "@type": "ListItem", position: 2, name: deal.category, item: `${BASE_URL}/?category=${encodeURIComponent(deal.category)}` },
      { "@type": "ListItem", position: 3, name: cleanTitle, item: `${BASE_URL}/deal/${id}` },
    ],
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(productJsonLd) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbJsonLd) }} />

      <div className="max-w-screen-lg mx-auto px-4 py-8">
        {/* 브레드크럼 */}
        <nav className="text-[12px] text-gray-400 mb-6 flex items-center gap-1.5">
          <Link href="/" className="hover:text-black transition-colors">홈</Link>
          <span>›</span>
          <Link href={`/?category=${encodeURIComponent(deal.category)}`} className="hover:text-black transition-colors">
            {deal.category}
          </Link>
          {retailer && brandSlug && (
            <>
              <span>›</span>
              <Link href={`/brand/${brandSlug}`} className="hover:text-black transition-colors">
                {retailer}
              </Link>
            </>
          )}
          <span>›</span>
          <span className="text-gray-600 truncate max-w-[200px]">{cleanTitle}</span>
        </nav>

        <div className="grid md:grid-cols-2 gap-8 lg:gap-12">
          {/* 이미지 */}
          <div className="aspect-square relative bg-gray-50 border border-gray-100">
            {deal.image_url ? (
              <Image src={deal.image_url} alt={deal.title} fill className="object-contain p-4" sizes="(max-width: 768px) 100vw, 50vw" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-6xl text-gray-200">📦</div>
            )}
            {dr > 0 && !isFree && (
              <div className="absolute top-3 left-3 bg-[#E31E24] text-white text-sm font-black px-2.5 py-1">
                -{dr}%
              </div>
            )}
            {deal.is_hot && (
              <div className="absolute top-3 right-3 bg-[#111] text-white text-xs font-bold px-2 py-1">HOT</div>
            )}
          </div>

          {/* 정보 */}
          <div>
            {/* 카테고리 + 소스 */}
            <div className="flex items-center gap-2 mb-2">
              <span className="text-[11px] text-gray-400">{deal.category}</span>
              <span className="text-gray-200">|</span>
              <span className="text-[11px] text-gray-400">
                {deal.source === "naver" ? "네이버 최저가" : deal.source === "community" ? "커뮤니티 제보" : deal.source}
              </span>
            </div>

            {/* 제목 */}
            <h1 className="text-xl font-bold text-gray-900 leading-snug mb-4">{deal.title}</h1>

            {/* 신뢰 뱃지 */}
            <div className="flex flex-wrap gap-1.5 mb-5">
              <span className="text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-100 px-2 py-0.5 font-medium">
                ✓ 정가 검증 완료
              </span>
              {dr > 0 && dr <= 65 && (
                <span className="text-[10px] text-blue-700 bg-blue-50 border border-blue-100 px-2 py-0.5 font-medium">
                  ✓ 이상 할인율 없음
                </span>
              )}
              {deal.source === "naver" && (
                <span className="text-[10px] text-gray-600 bg-gray-50 border border-gray-100 px-2 py-0.5 font-medium">
                  ✓ 공식 판매처 확인
                </span>
              )}
            </div>

            {/* 가격 */}
            <div className="border-t border-gray-100 pt-4 mb-5">
              <div className="flex items-baseline gap-2 mb-1">
                {dr > 0 && !isFree && (
                  <span className="text-2xl font-black text-[#E31E24]">-{dr}%</span>
                )}
                <span className={`text-3xl font-black ${isFree ? "text-emerald-600" : "text-gray-900"}`}>
                  {isFree ? "무료" : formatPrice(deal.sale_price)}
                </span>
              </div>
              {deal.original_price > deal.sale_price && !isFree && (
                <p className="text-sm text-gray-400 line-through">{formatPrice(deal.original_price)}</p>
              )}
              {saved > 100 && !isFree && (
                <p className="text-sm text-emerald-600 font-semibold mt-1">{formatPrice(saved)} 절약 ↓</p>
              )}
            </div>

            {/* 신뢰지수 */}
            {deal.trust && (
              <div className="bg-gray-50 border border-gray-100 p-3 mb-5 rounded-sm">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-base">{deal.trust.emoji}</span>
                  <span className="text-sm font-bold text-gray-800">{deal.trust.label}</span>
                  <span className="text-xs text-gray-400">신뢰지수 {deal.trust.score}점</span>
                </div>
                <p className="text-xs text-gray-500">{deal.trust.comment}</p>
                {deal.price_stats?.data_days > 0 && (
                  <p className="text-xs text-gray-400 mt-1">
                    {deal.price_stats.data_days}일간 수집 | 최저 {formatPrice(deal.price_stats.min_price)} | 평균 {formatPrice(deal.price_stats.avg_price)}
                  </p>
                )}
              </div>
            )}

            {/* 가격 히스토리 차트 */}
            {deal.source === "naver" && (
              <div className="mb-5">
                <p className="text-xs font-bold text-gray-600 mb-2">가격 추이</p>
                <PriceChart
                  data={(deal as any).chart_data || []}
                  currentPrice={deal.sale_price}
                  minPrice={(deal as any).price_stats?.min_price}
                  avgPrice={(deal as any).price_stats?.avg_price}
                />
              </div>
            )}

            {/* 구매 버튼 */}
            <a
              href={targetUrl}
              target="_blank"
              rel="noopener noreferrer sponsored"
              className="block w-full text-center bg-[#111] text-white font-bold py-4 text-sm hover:bg-[#333] transition-colors mb-3"
            >
              {isFree ? "지금 무료로 받기" : "지금 최저가 구매"}
            </a>

            {/* 공유 버튼 */}
            <div className="mb-3">
              <ShareButtons
                title={deal.title}
                salePrice={deal.sale_price}
                discountRate={deal.discount_rate}
                imageUrl={deal.image_url}
                dealUrl={`${BASE_URL}/deal/${id}`}
              />
            </div>

            <Link
              href="/"
              className="block w-full text-center border border-gray-200 text-gray-500 text-sm py-3 hover:border-gray-400 transition-colors"
            >
              ← 다른 딜 보기
            </Link>

            {/* 조회수 */}
            <p className="text-[11px] text-gray-300 text-center mt-3">조회 {deal.views?.toLocaleString() || 0}회</p>
          </div>
        </div>

        {/* 딜 가격 히스토리 차트 (deal_price_log 기반) */}
        <PriceHistoryChart
          dealId={deal.id}
          salePrice={deal.sale_price}
          originalPrice={deal.original_price}
        />

        {/* 관련 딜 */}
        {relatedDeals.length > 0 && (
          <section className="mt-10 border-t pt-6">
            <h2 className="text-[15px] font-bold text-gray-900 mb-4">
              {deal.category} 관련 딜
            </h2>
            <div className="grid grid-cols-3 gap-3">
              {relatedDeals.map((r) => (
                <Link key={r.id} href={`/deal/${r.id}`}>
                  <DealCard deal={r} />
                </Link>
              ))}
            </div>
          </section>
        )}

        {/* 관련 카테고리 링크 */}
        <div className="mt-12 pt-8 border-t border-gray-100">
          <h2 className="text-sm font-bold text-gray-700 mb-3">{deal.category} 다른 딜 보기</h2>
          <Link
            href={`/?category=${encodeURIComponent(deal.category)}`}
            className="inline-block text-sm text-gray-500 border border-gray-200 px-4 py-2 hover:border-gray-400 transition-colors"
          >
            {deal.category} 전체 딜 →
          </Link>
          {retailer && brandSlug && (
            <Link
              href={`/brand/${brandSlug}`}
              className="inline-block text-sm text-gray-500 border border-gray-200 px-4 py-2 hover:border-gray-400 transition-colors ml-2"
            >
              {retailer} 브랜드 딜 →
            </Link>
          )}
        </div>
      </div>
    </>
  );
}
