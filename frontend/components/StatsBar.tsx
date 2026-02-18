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

export default async function StatsBar() {
  const stats = await fetchStats();
  if (!stats) return null;

  const avgDiscount = stats.avg_discount > 0 ? `${stats.avg_discount}%` : "-";
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
      <div className="max-w-screen-xl mx-auto px-4 py-3">
        <div className="flex items-center gap-8 overflow-x-auto scrollbar-hide">
          {items.map((item) => (
            <div key={item.label} className="flex items-center gap-2 shrink-0">
              <span className="text-[11px] text-gray-400">{item.label}</span>
              <span className="text-[13px] font-bold text-gray-900">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
