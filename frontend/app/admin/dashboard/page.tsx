"use client";

import { useEffect, useState } from "react";
import { getAdminMetrics, AdminMetrics } from "@/lib/admin-api";

function KPICard({
  label,
  value,
  unit = "",
  highlight = false,
}: {
  label: string;
  value: number | string;
  unit?: string;
  highlight?: boolean;
}) {
  return (
    <div className={`p-5 border ${highlight ? "bg-gray-900 border-gray-900" : "bg-white border-gray-200"}`}>
      <p className={`text-xs font-medium uppercase tracking-wider mb-2 ${highlight ? "text-gray-400" : "text-gray-400"}`}>
        {label}
      </p>
      <p className={`text-2xl font-black ${highlight ? "text-white" : "text-gray-900"}`}>
        {typeof value === "number" ? value.toLocaleString() : value}
        {unit && <span className="text-sm font-medium text-gray-400 ml-1">{unit}</span>}
      </p>
    </div>
  );
}

export default function AdminDashboardPage() {
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const load = () =>
      getAdminMetrics()
        .then(setMetrics)
        .catch((e: Error) => setError(e.message))
        .finally(() => setLoading(false));

    load();
    const timer = setInterval(load, 30_000); // 30초마다 자동 갱신
    return () => clearInterval(timer);
  }, []);

  if (loading) {
    return (
      <div className="p-8 text-sm text-gray-400">로딩 중...</div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="p-8 text-sm text-[#E31E24]">
        오류: {error || "데이터를 불러올 수 없습니다."}
      </div>
    );
  }

  const maxPv = Math.max(...metrics.trend.map((t) => t.pv), 1);

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-xl font-black text-gray-900">대시보드</h1>
        <p className="text-sm text-gray-400 mt-0.5">{metrics.date} 기준</p>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-8">
        <KPICard label="홈 방문자" value={metrics.today.pv} unit="명" highlight />
        <KPICard label="딜 노출" value={metrics.today.impressions ?? 0} />
        <KPICard label="딜 오픈" value={metrics.today.deal_opens} />
        <KPICard label="구매클릭" value={metrics.today.clicks} />
        <KPICard label="활성딜" value={metrics.today.active_deals} unit="개" />
        <KPICard label="오늘신규" value={metrics.today.new_deals} unit="건" />
      </div>

      {/* 7일 추이 */}
      <div className="bg-white border border-gray-200 p-5 mb-6">
        <h2 className="text-sm font-bold text-gray-900 mb-4">최근 7일 PV 추이</h2>
        <div className="flex items-end gap-2 h-32">
          {metrics.trend.map((day) => {
            const pct = Math.max((day.pv / maxPv) * 100, 2);
            const isToday = day.date === metrics.date;
            return (
              <div key={day.date} className="flex-1 flex flex-col items-center gap-1">
                <span className="text-[10px] text-gray-400">{day.pv}</span>
                <div
                  className={`w-full transition-all ${
                    isToday ? "bg-[#E31E24]" : "bg-gray-200"
                  }`}
                  style={{ height: `${pct}%` }}
                />
                <span className="text-[9px] text-gray-300 rotate-0">
                  {day.date.slice(5)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Top 10 */}
      {metrics.top10.length > 0 && (
        <div className="bg-white border border-gray-200 p-5">
          <h2 className="text-sm font-bold text-gray-900 mb-4">
            오늘 Top 10 딜 (클릭 기준)
          </h2>
          <div className="divide-y divide-gray-100">
            {metrics.top10.map((deal, idx) => (
              <div key={deal.id} className="flex items-center py-2.5 gap-3">
                <span className="text-sm font-black text-gray-300 w-5 shrink-0">
                  {idx + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-gray-800 truncate">
                    {deal.title}
                  </p>
                  <p className="text-[10px] text-gray-400 mt-0.5">
                    {deal.sale_price.toLocaleString()}원 ·{" "}
                    {Math.round(deal.discount_rate)}% · {deal.source}
                  </p>
                </div>
                <span className="text-xs font-bold text-[#E31E24] shrink-0">
                  {deal.clicks_today}클릭
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
