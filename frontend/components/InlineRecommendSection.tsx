"use client";

import { useEffect, useState } from "react";
import { Deal } from "@/lib/api";
import DealCard from "./DealCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";

interface Props {
  excludeIds: string[];
}

export default function InlineRecommendSection({ excludeIds }: Props) {
  const [deals, setDeals] = useState<Deal[]>([]);

  useEffect(() => {
    const fetchDeals = async () => {
      try {
        const res = await fetch(
          `${API_BASE}/api/deals?hot_only=true&sort=hot_score&size=8`
        );
        if (!res.ok) return;
        const data = await res.json();
        const items: Deal[] = data.items ?? [];
        const filtered = items
          .filter((d) => !excludeIds.includes(String(d.id)))
          .slice(0, 4);
        setDeals(filtered);
      } catch {
        // 조용히 실패 — 추천 섹션은 없어도 그만
      }
    };

    fetchDeals();
  }, [excludeIds.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  if (deals.length === 0) return null;

  return (
    <div className="bg-gray-50 rounded-lg p-4 my-4">
      <p className="text-sm font-semibold text-gray-500">✨ 혹시 이런 딜도?</p>
      <div className="flex gap-3 overflow-x-auto pb-2 mt-3 scrollbar-hide">
        {deals.map((deal) => (
          <div key={deal.id} className="min-w-[140px] flex-shrink-0">
            <DealCard deal={deal} />
          </div>
        ))}
      </div>
    </div>
  );
}
