import { Deal, formatPrice } from "@/lib/api";
import Link from "next/link";

interface HotBannerProps {
  deals: Deal[];
}

export default function HotBanner({ deals }: HotBannerProps) {
  if (deals.length === 0) return null;

  return (
    <section className="border-b border-gray-200 bg-white">
      <div className="max-w-screen-xl mx-auto px-4 py-8">
        {/* 섹션 헤더 */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <p className="text-[11px] font-semibold text-[#E31E24] tracking-widest uppercase mb-1">
              Real-time Hot Deal
            </p>
            <h2 className="text-xl font-black text-gray-900 tracking-tight">
              지금 가장 인기 있는 딜
            </h2>
          </div>
          <Link
            href="/?hot_only=true"
            className="text-xs text-gray-500 hover:text-gray-900 underline underline-offset-2 transition-colors"
          >
            전체보기
          </Link>
        </div>

        {/* 가로 스크롤 딜 목록 */}
        <div className="flex gap-4 overflow-x-auto scrollbar-hide pb-2">
          {deals.slice(0, 8).map((deal, idx) => {
            const targetUrl = deal.affiliate_url || deal.product_url;
            const saved = deal.original_price - deal.sale_price;
            return (
              <a
                key={deal.id}
                href={targetUrl}
                target="_blank"
                rel="noopener noreferrer sponsored"
                className="group shrink-0 w-[180px]"
              >
                {/* 이미지 */}
                <div className="relative overflow-hidden bg-gray-100 aspect-square mb-2">
                  {deal.image_url ? (
                    <img
                      src={deal.image_url}
                      alt={deal.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-3xl bg-gray-100" />
                  )}
                  {/* 순위 */}
                  <div className="absolute top-2 left-2 w-6 h-6 bg-[#111] text-white text-xs font-black flex items-center justify-center">
                    {idx + 1}
                  </div>
                  <div className="absolute top-2 right-2 bg-[#E31E24] text-white text-xs font-black px-1.5 py-0.5">
                    -{Math.round(deal.discount_rate)}%
                  </div>
                </div>

                {/* 텍스트 */}
                <p className="text-[12px] text-gray-700 line-clamp-2 leading-snug mb-1 group-hover:text-black transition-colors">
                  {deal.title}
                </p>
                <p className="text-[14px] font-black text-gray-900">
                  {formatPrice(deal.sale_price)}
                </p>
                <p className="text-[11px] text-gray-400 line-through">
                  {formatPrice(deal.original_price)}
                </p>
              </a>
            );
          })}
        </div>
      </div>
    </section>
  );
}
