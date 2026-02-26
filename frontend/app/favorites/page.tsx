"use client";
import { useEffect, useState } from "react";
import { useFavorites } from "@/hooks/useFavorites";
import DealCard from "@/components/DealCard";
import { DealGridSkeleton } from "@/components/DealCardSkeleton";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";

export default function FavoritesPage() {
  const { favIds, count, toggle } = useFavorites();
  const [deals, setDeals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (favIds.length === 0) { setLoading(false); return; }
    setError(false);
    fetch(`${API_BASE}/api/deals/by-ids?ids=${favIds.join(",")}`)
      .then(r => {
        if (!r.ok) throw new Error("load failed");
        return r.json();
      })
      .then(setDeals)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [JSON.stringify(favIds)]);

  const handleRetry = () => {
    if (favIds.length === 0) return;
    setLoading(true);
    setError(false);
    fetch(`${API_BASE}/api/deals/by-ids?ids=${favIds.join(",")}`)
      .then(r => {
        if (!r.ok) throw new Error("load failed");
        return r.json();
      })
      .then(setDeals)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  };

  return (
    <div className="max-w-screen-xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-xl font-bold">찜한 딜</h1>
        {count > 0 && <span className="text-sm text-gray-400">{count}개</span>}
      </div>

      {/* 로딩: 실제 카드 레이아웃과 동일한 스켈레톤 */}
      {loading ? (
        <DealGridSkeleton count={Math.min(count || 4, 10)} />
      ) : error ? (
        /* 에러 상태 */
        <div className="py-20 text-center">
          <p className="text-3xl mb-3" aria-hidden="true">😵</p>
          <p className="text-gray-500 text-sm mb-4">딜 정보를 불러오지 못했어요</p>
          <button
            onClick={handleRetry}
            className="flex items-center gap-2 mx-auto text-sm font-semibold text-gray-700 border border-gray-300 px-4 py-2 hover:border-gray-700 hover:text-black transition-colors active:scale-95"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="23 4 23 10 17 10" />
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
            </svg>
            다시 불러오기
          </button>
        </div>
      ) : favIds.length === 0 ? (
        /* 빈 상태 */
        <div className="py-20 text-center text-gray-400">
          <p className="text-3xl mb-3" aria-hidden="true">🤍</p>
          <p>딜 카드의 ♡ 버튼을 눌러 찜해보세요</p>
        </div>
      ) : (
        /* 딜 그리드 */
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {deals.map(d => <DealCard key={d.id} deal={d} />)}
        </div>
      )}
    </div>
  );
}
