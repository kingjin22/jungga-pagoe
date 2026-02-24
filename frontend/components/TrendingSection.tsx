"use client";

import { useRouter } from "next/navigation";
import DealCard from "./DealCard";
import type { Deal } from "@/lib/api";

interface Props {
  deals: Deal[];
}

export default function TrendingSection({ deals }: Props) {
  const router = useRouter();

  if (!deals || deals.length === 0) return null;

  // 조회수가 모두 0이면 섹션 숨김
  const hasViews = deals.some((d) => (d.views ?? 0) > 0);
  if (!hasViews) return null;

  return (
    <section className="mb-8">
      <div className="flex items-center gap-2 mb-3">
        <span className="inline-block w-2 h-2 rounded-full bg-[#E31E24] animate-pulse" />
        <h2 className="text-[13px] font-bold text-gray-700 tracking-tight">지금 인기</h2>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {deals.map((deal) => (
          <DealCard
            key={deal.id}
            deal={deal}
            onClick={() => router.push(`/deal/${deal.id}`)}
          />
        ))}
      </div>
    </section>
  );
}
