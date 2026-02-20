const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

async function fetchStats() {
  try {
    const res = await fetch(`${API_BASE}/api/stats`, { next: { revalidate: 60 } });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

function lastUpdatedText(lastUpdatedAt?: string): string {
  if (!lastUpdatedAt) return "10분마다 업데이트";
  const diff = Math.floor((Date.now() - new Date(lastUpdatedAt).getTime()) / 60000);
  if (diff <= 0) return "방금 업데이트";
  if (diff === 1) return "1분 전 업데이트";
  if (diff < 10) return `${diff}분 전 업데이트`;
  return "10분마다 업데이트";
}

export default async function StatsBar() {
  const stats = await fetchStats();
  if (!stats) return null;

  const avgDiscount = stats.avg_discount > 0 ? `${stats.avg_discount}%` : "-";

  // 방문자 수는 공개 노출 안 함 (admin 전용)
  const items = [
    { label: "전체 딜", value: `${stats.total_deals.toLocaleString()}개` },
    { label: "HOT 딜", value: `${stats.hot_deals.toLocaleString()}개` },
    { label: "평균 할인율", value: avgDiscount },
    { label: "오늘 등록", value: `${stats.today_added.toLocaleString()}개` },
    { label: "커뮤니티", value: `${(stats.by_source?.community || 0).toLocaleString()}개` },
    { label: "네이버", value: `${(stats.by_source?.naver || 0).toLocaleString()}개` },
  ];

  return (
    <div className="bg-[#FAFAFA] border-b border-gray-200">
      <div className="max-w-screen-xl mx-auto px-4 py-2.5">
        <div className="flex items-center gap-6 overflow-x-auto scrollbar-hide">
          {/* 업데이트 시간 — 맨 앞 */}
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[11px] text-gray-400">{lastUpdatedText(stats.last_updated_at)}</span>
          </div>
          <span className="text-gray-200 text-xs shrink-0">|</span>
          {items.map((item) => (
            <div key={item.label} className="flex items-center gap-1.5 shrink-0">
              <span className="text-[11px] text-gray-400">{item.label}</span>
              <span className="text-[13px] font-bold text-gray-900">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
