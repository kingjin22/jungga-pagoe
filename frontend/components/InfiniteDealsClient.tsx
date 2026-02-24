"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Deal } from "@/lib/api";
import DealCard from "./DealCard";
import DealModal from "./DealModal";

const PAGE_SIZE = 20;
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Props {
  initialDeals: Deal[];
  filterParams: {
    category?: string;
    source?: string;
    search?: string;
    sort?: string;
    hot_only?: string;
    price_min?: string;
    price_max?: string;
  };
}

export default function InfiniteDealsClient({ initialDeals, filterParams }: Props) {
  const [deals, setDeals] = useState<Deal[]>(initialDeals);
  const [offset, setOffset] = useState(initialDeals.length);
  const [hasMore, setHasMore] = useState(initialDeals.length >= PAGE_SIZE);
  const [loading, setLoading] = useState(false);
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);
  const loaderRef = useRef<HTMLDivElement>(null);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    setLoading(true);
    try {
      const q = new URLSearchParams({
        offset: String(offset),
        size: String(PAGE_SIZE),
      });
      if (filterParams.category) q.set("category", filterParams.category);
      if (filterParams.source) q.set("source", filterParams.source);
      if (filterParams.search) q.set("search", filterParams.search);
      if (filterParams.sort) q.set("sort", filterParams.sort);
      if (filterParams.hot_only === "true") q.set("hot_only", "true");
      if (filterParams.price_min) q.set("price_min", filterParams.price_min);
      if (filterParams.price_max) q.set("price_max", filterParams.price_max);

      const res = await fetch(`${API_BASE}/api/deals?${q}`);
      if (!res.ok) throw new Error("딜 로드 실패");
      const data = await res.json();
      const newDeals: Deal[] = data.items ?? [];
      if (newDeals.length < PAGE_SIZE) setHasMore(false);
      setDeals((prev) => [...prev, ...newDeals]);
      setOffset((prev) => prev + newDeals.length);
    } catch {
      // 네트워크 오류 시 조용히 실패 — 재시도는 다음 스크롤 시
    } finally {
      setLoading(false);
    }
  }, [loading, hasMore, offset, filterParams]);

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) loadMore();
      },
      { threshold: 0.1 }
    );
    if (loaderRef.current) observer.observe(loaderRef.current);
    return () => observer.disconnect();
  }, [loadMore]);

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-x-4 gap-y-8">
        {deals.map((deal) => (
          <DealCard key={deal.id} deal={deal} onClick={setSelectedDeal} />
        ))}
      </div>

      {/* IntersectionObserver 트리거 영역 */}
      <div ref={loaderRef} className="h-10 flex items-center justify-center mt-4">
        {loading && (
          <span className="text-[12px] text-gray-400">딜 불러오는 중...</span>
        )}
        {!hasMore && deals.length > 0 && (
          <span className="text-[12px] text-gray-300">모든 딜을 확인했습니다</span>
        )}
      </div>

      <DealModal deal={selectedDeal} onClose={() => setSelectedDeal(null)} />
    </>
  );
}
