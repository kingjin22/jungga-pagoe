"use client";

import { Deal, formatPrice } from "@/lib/api";

interface HotBannerProps {
  deals: Deal[];
}

export default function HotBanner({ deals }: HotBannerProps) {
  if (deals.length === 0) return null;

  return (
    <section className="bg-gradient-to-r from-[#E31E24] to-[#FF5252] text-white rounded-2xl p-5 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-2xl">🔥</span>
        <h2 className="text-xl font-black">지금 가장 핫한 딜</h2>
        <span className="text-xs bg-white/20 px-2 py-0.5 rounded-full">LIVE</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {deals.slice(0, 3).map((deal) => {
          const targetUrl = deal.affiliate_url || deal.product_url;
          return (
            <a
              key={deal.id}
              href={targetUrl}
              target="_blank"
              rel="noopener noreferrer sponsored"
              className="bg-white/10 hover:bg-white/20 transition-colors rounded-xl p-3 flex items-center gap-3"
            >
              {deal.image_url && (
                <img
                  src={deal.image_url}
                  alt={deal.title}
                  className="w-12 h-12 rounded-lg object-cover shrink-0"
                />
              )}
              <div className="min-w-0">
                <p className="text-xs text-white/80 truncate">{deal.title}</p>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="font-black text-yellow-300">
                    {formatPrice(deal.sale_price)}
                  </span>
                  <span className="text-xs bg-yellow-300 text-red-800 font-bold px-1 rounded">
                    -{Math.round(deal.discount_rate)}%
                  </span>
                </div>
              </div>
            </a>
          );
        })}
      </div>
    </section>
  );
}
