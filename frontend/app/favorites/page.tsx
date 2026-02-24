"use client";
import { useEffect, useState } from "react";
import { useFavorites } from "@/hooks/useFavorites";
import DealCard from "@/components/DealCard";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";

export default function FavoritesPage() {
  const { favIds, count, toggle } = useFavorites();
  const [deals, setDeals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (favIds.length === 0) { setLoading(false); return; }
    fetch(`${API_BASE}/api/deals/by-ids?ids=${favIds.join(",")}`)
      .then(r => r.json())
      .then(setDeals)
      .finally(() => setLoading(false));
  }, [JSON.stringify(favIds)]);

  return (
    <div className="max-w-screen-xl mx-auto px-4 py-8">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-xl font-bold">찜한 딜</h1>
        {count > 0 && <span className="text-sm text-gray-400">{count}개</span>}
      </div>
      {loading ? (
        <p className="text-gray-400 text-sm">불러오는 중...</p>
      ) : favIds.length === 0 ? (
        <div className="py-20 text-center text-gray-400">
          <p className="text-3xl mb-3">🤍</p>
          <p>딜 카드의 ♡ 버튼을 눌러 찜해보세요</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {deals.map(d => <DealCard key={d.id} deal={d} />)}
        </div>
      )}
    </div>
  );
}
