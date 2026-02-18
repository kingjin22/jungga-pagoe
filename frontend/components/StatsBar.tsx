const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface Stats {
  total_deals: number;
  hot_deals: number;
  by_source: { coupang: number; naver: number; community: number };
  today_added: number;
  avg_discount: number;
}

async function fetchStats(): Promise<Stats | null> {
  try {
    const res = await fetch(`${API_BASE}/api/stats`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export default async function StatsBar() {
  const stats = await fetchStats();

  if (!stats) return null;

  const cards = [
    {
      label: "전체 딜",
      value: stats.total_deals.toLocaleString(),
      suffix: "개",
      color: "text-blue-600",
      bg: "bg-blue-50",
      icon: "🛍️",
    },
    {
      label: "핫딜",
      value: stats.hot_deals.toLocaleString(),
      suffix: "개",
      color: "text-red-600",
      bg: "bg-red-50",
      icon: "🔥",
    },
    {
      label: "평균 할인율",
      value: stats.avg_discount.toFixed(1),
      suffix: "%",
      color: "text-orange-600",
      bg: "bg-orange-50",
      icon: "📉",
    },
    {
      label: "오늘 등록",
      value: stats.today_added.toLocaleString(),
      suffix: "개",
      color: "text-green-600",
      bg: "bg-green-50",
      icon: "🆕",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
      {cards.map((card) => (
        <div
          key={card.label}
          className={`${card.bg} rounded-2xl p-4 flex items-center gap-3`}
        >
          <span className="text-2xl">{card.icon}</span>
          <div>
            <p className="text-xs text-gray-500 font-medium">{card.label}</p>
            <p className={`text-xl font-black ${card.color}`}>
              {card.value}
              <span className="text-sm font-bold">{card.suffix}</span>
            </p>
          </div>
        </div>
      ))}
    </div>
  );
}
