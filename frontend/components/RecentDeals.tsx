"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { useRecentDeals } from "@/hooks/useRecentDeals";
import { formatPrice } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";

export default function RecentDeals() {
  const { recentIds } = useRecentDeals();
  const [deals, setDeals] = useState<any[]>([]);

  useEffect(() => {
    if (recentIds.length === 0) return;
    fetch(`${API_BASE}/api/deals/by-ids?ids=${recentIds.join(",")}`)
      .then(r => r.json())
      .then(data => {
        const map = Object.fromEntries(data.map((d: any) => [d.id, d]));
        setDeals(recentIds.map(id => map[id]).filter(Boolean));
      })
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [recentIds.join(",")]);

  if (deals.length === 0) return null;

  return (
    <section className="mt-8">
      <h2 className="text-[13px] font-semibold text-gray-500 mb-3 tracking-wide uppercase">최근 본 딜</h2>
      <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
        {deals.map(d => (
          <Link key={d.id} href={`/deal/${d.id}`} className="w-36 shrink-0 group">
            <div className="relative aspect-square bg-gray-100 overflow-hidden mb-1">
              {d.image_url ? (
                <Image src={d.image_url} alt={d.title} fill sizes="144px" className="object-cover" />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-2xl">📦</div>
              )}
              {d.discount_rate > 0 && (
                <div className="absolute top-0 left-0 bg-[#E31E24] text-white text-[10px] font-bold px-1.5 py-0.5 leading-none">
                  -{Math.round(d.discount_rate)}%
                </div>
              )}
            </div>
            <p className="text-[12px] text-gray-800 line-clamp-2 leading-snug group-hover:text-black transition-colors">
              {d.title}
            </p>
            <p className="text-[13px] font-black text-gray-900 mt-0.5">
              {d.sale_price === 0 ? "무료" : formatPrice(d.sale_price)}
            </p>
          </Link>
        ))}
      </div>
    </section>
  );
}
