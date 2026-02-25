"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Deal } from "@/lib/api";
import DealCard from "./DealCard";
import DealModal from "./DealModal";
import DealCardSkeleton from "./DealCardSkeleton";

const PAGE_SIZE = 20;
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";

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
  const [error, setError] = useState(false);
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);
  const loaderRef = useRef<HTMLDivElement>(null);

  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    setLoading(true);
    setError(false);
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
      // 에러 발생 시 hasMore 유지 → 사용자가 retry 가능
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [loading, hasMore, offset, filterParams]);

  const handleRetry = () => {
    setError(false);
    loadMore();
  };

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !error) loadMore();
      },
      { threshold: 0.1 }
    );
    if (loaderRef.current) observer.observe(loaderRef.current);
    return () => observer.disconnect();
  }, [loadMore, error]);

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-x-4 gap-y-8">
        {deals.map((deal) => (
          <DealCard key={deal.id} deal={deal} onClick={setSelectedDeal} />
        ))}
      </div>

      {/* 추가 로딩 스켈레톤 */}
      {loading && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-x-4 gap-y-8 mt-8">
          {Array.from({ length: 10 }).map((_, i) => <DealCardSkeleton key={i} />)}
        </div>
      )}

      {/* 에러 상태 — 재시도 버튼 */}
      {error && (
        <div className="flex flex-col items-center gap-3 py-8 mt-4">
          <p className="text-sm text-gray-400">딜을 불러오는 중 문제가 발생했습니다</p>
          <button
            onClick={handleRetry}
            className="flex items-center gap-1.5 text-sm font-semibold text-gray-700 border border-gray-300 px-4 py-2 hover:border-gray-700 hover:text-black transition-colors active:scale-95"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="23 4 23 10 17 10" />
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
            </svg>
            다시 불러오기
          </button>
        </div>
      )}

      {/* IntersectionObserver 트리거 영역 */}
      <div ref={loaderRef} className="h-10 flex items-center justify-center mt-4">
        {!hasMore && !error && deals.length > 0 && (
          <span className="text-[12px] text-gray-300">모든 딜을 확인했습니다</span>
        )}
      </div>

      <DealModal deal={selectedDeal} onClose={() => setSelectedDeal(null)} />
    </>
  );
}
