const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";

async function fetchTodayBest() {
  const res = await fetch(
    `${API_BASE}/api/deals?sort=discount&size=5&hot_only=true`,
    { next: { revalidate: 300 } }
  );
  if (!res.ok) return [];
  const data = await res.json();
  return data.items ?? [];
}

export default async function TodayBest() {
  const deals = await fetchTodayBest();
  if (!deals.length) return null;

  return (
    <section className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-bold flex items-center gap-2">
          <span className="text-[#E31E24]">🔥</span> 지금 가장 핫한 딜
        </h2>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
        {deals.map((deal: any, i: number) => (
          <a key={deal.id} href={`/deal/${deal.id}`}
            className="flex sm:flex-col gap-3 sm:gap-0 border border-gray-100 rounded-lg overflow-hidden hover:border-gray-300 transition-colors group">
            {deal.image_url && (
              <div className="w-20 sm:w-full aspect-square sm:aspect-square overflow-hidden bg-gray-50 shrink-0">
                <img src={deal.image_url} alt={deal.title}
                  className="w-full h-full object-contain group-hover:scale-105 transition-transform duration-200" />
              </div>
            )}
            <div className="p-2 flex flex-col justify-between flex-1">
              <p className="text-[11px] text-gray-500 truncate">{deal.brand || deal.category}</p>
              <p className="text-[12px] font-medium line-clamp-2 leading-tight mt-0.5">{deal.title}</p>
              <div className="mt-1.5 flex items-center gap-1.5">
                <span className="text-[#E31E24] font-bold text-sm">-{Math.round(deal.discount_rate)}%</span>
                <span className="text-[13px] font-bold">{deal.sale_price?.toLocaleString()}원</span>
              </div>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}
