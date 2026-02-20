"use client";

import { useEffect, useState } from "react";
import { getAdminMetrics, AdminMetrics } from "@/lib/admin-api";

/* ── SVG 라인 차트 ── */
function LineChart({
  data,
  valueKey,
  color = "#00C73C",
  height = 120,
}: {
  data: { date: string; pv: number; clicks: number; deal_opens: number }[];
  valueKey: "pv" | "clicks" | "deal_opens";
  color?: string;
  height?: number;
}) {
  const values = data.map((d) => d[valueKey]);
  const max = Math.max(...values, 1);
  const W = 560;
  const H = height;
  const PAD = { top: 16, bottom: 28, left: 32, right: 12 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;
  const step = chartW / Math.max(data.length - 1, 1);

  const points = data.map((d, i) => ({
    x: PAD.left + i * step,
    y: PAD.top + chartH - (d[valueKey] / max) * chartH,
    val: d[valueKey],
    date: d.date,
  }));

  const pathD = points
    .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
    .join(" ");

  const fillD = `${pathD} L ${points[points.length - 1].x} ${PAD.top + chartH} L ${PAD.left} ${PAD.top + chartH} Z`;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height }}>
      {/* 그리드 라인 */}
      {[0, 0.5, 1].map((pct) => {
        const y = PAD.top + chartH * (1 - pct);
        const val = Math.round(max * pct);
        return (
          <g key={pct}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y} y2={y}
              stroke="#f0f0f0" strokeWidth="1" />
            <text x={PAD.left - 4} y={y + 4} textAnchor="end"
              fontSize="9" fill="#aaa">{val}</text>
          </g>
        );
      })}

      {/* 영역 fill */}
      <path d={fillD} fill={color} fillOpacity="0.08" />

      {/* 라인 */}
      <path d={pathD} fill="none" stroke={color} strokeWidth="2"
        strokeLinejoin="round" strokeLinecap="round" />

      {/* 포인트 */}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="3.5"
          fill="white" stroke={color} strokeWidth="2" />
      ))}

      {/* X축 날짜 */}
      {points.map((p, i) => (
        <text key={i} x={p.x} y={H - 2} textAnchor="middle"
          fontSize="9" fill="#aaa">
          {p.date.slice(5).replace("-", "/")}
        </text>
      ))}
    </svg>
  );
}

/* ── 소스 뱃지 색상 ── */
const SOURCE_COLOR: Record<string, string> = {
  coupang: "bg-[#E31E24] text-white",
  naver:   "bg-green-600 text-white",
  community: "bg-blue-500 text-white",
  admin:   "bg-gray-600 text-white",
};

export default function AdminDashboardPage() {
  const [metrics, setMetrics] = useState<AdminMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"pv" | "clicks" | "deal_opens">("pv");

  useEffect(() => {
    const load = () =>
      getAdminMetrics()
        .then(setMetrics)
        .catch((e: Error) => setError(e.message))
        .finally(() => setLoading(false));
    load();
    const timer = setInterval(load, 30_000);
    return () => clearInterval(timer);
  }, []);

  if (loading) return <div className="p-8 text-sm text-gray-400">로딩 중...</div>;
  if (error || !metrics) return (
    <div className="p-8 text-sm text-red-500">오류: {error || "데이터 없음"}</div>
  );

  const now = new Date().toLocaleString("ko-KR", {
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });

  const TAB_CONFIG = {
    pv:         { label: "방문자수", today: metrics.today.pv,         color: "#00C73C" },
    clicks:     { label: "구매클릭",  today: metrics.today.clicks,     color: "#E31E24" },
    deal_opens: { label: "딜 오픈",   today: metrics.today.deal_opens, color: "#2563eb" },
  };

  return (
    <div className="p-6 max-w-5xl">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-lg font-black text-gray-900">방문 분석</h1>
        <span className="text-xs text-gray-400">{now} 기준</span>
      </div>

      {/* KPI 요약 */}
      <div className="grid grid-cols-3 lg:grid-cols-6 gap-2 mb-6">
        {[
          { label: "방문자",   val: metrics.today.pv,           hi: true },
          { label: "딜 노출",  val: metrics.today.impressions ?? 0 },
          { label: "딜 오픈",  val: metrics.today.deal_opens },
          { label: "구매클릭", val: metrics.today.clicks },
          { label: "활성딜",   val: metrics.today.active_deals,  unit: "개" },
          { label: "오늘신규", val: metrics.today.new_deals,     unit: "건" },
        ].map(({ label, val, hi, unit }) => (
          <div key={label}
            className={`p-3 border text-center ${hi ? "bg-gray-900 border-gray-900" : "bg-white border-gray-200"}`}>
            <p className={`text-[10px] font-medium mb-1 ${hi ? "text-gray-400" : "text-gray-400"}`}>{label}</p>
            <p className={`text-xl font-black ${hi ? "text-white" : "text-gray-900"}`}>
              {(val ?? 0).toLocaleString()}
              {unit && <span className="text-xs font-normal text-gray-400 ml-0.5">{unit}</span>}
            </p>
          </div>
        ))}
      </div>

      {/* 라인 차트 */}
      <div className="bg-white border border-gray-200 p-5 mb-6">
        {/* 탭 */}
        <div className="flex gap-0 border-b border-gray-200 mb-4">
          {(Object.entries(TAB_CONFIG) as [keyof typeof TAB_CONFIG, typeof TAB_CONFIG[keyof typeof TAB_CONFIG]][]).map(([key, cfg]) => (
            <button
              key={key}
              onClick={() => setActiveTab(key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === key
                  ? "border-[#00C73C] text-[#00C73C]"
                  : "border-transparent text-gray-400 hover:text-gray-700"
              }`}
            >
              {cfg.label}
            </button>
          ))}
          <span className="ml-auto text-sm text-gray-500 self-center pr-1">
            오늘 <strong className="text-gray-900">{TAB_CONFIG[activeTab].today.toLocaleString()}</strong>
          </span>
        </div>

        <LineChart
          data={metrics.trend}
          valueKey={activeTab}
          color={TAB_CONFIG[activeTab].color}
          height={140}
        />
      </div>

      {/* 하단 2열 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* 딜 조회 순위 */}
        <div className="bg-white border border-gray-200 p-5">
          <h2 className="text-sm font-bold text-gray-900 mb-3 pb-2 border-b border-gray-100">
            딜 클릭 순위
          </h2>
          {metrics.top10.length === 0 ? (
            <p className="text-xs text-gray-400 py-4 text-center">오늘 클릭 데이터가 없습니다.</p>
          ) : (
            <div className="divide-y divide-gray-50">
              {metrics.top10.slice(0, 8).map((deal, idx) => {
                const topIdx = idx === 0 ? 0 : metrics.top10.findIndex(d => d.clicks_today < deal.clicks_today);
                const rank = idx + 1;
                return (
                  <div key={deal.id} className="flex items-center py-2.5 gap-2">
                    <span className={`text-xs font-black w-4 shrink-0 ${rank <= 3 ? "text-[#E31E24]" : "text-gray-400"}`}>
                      {rank}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-gray-800 truncate leading-snug">
                        {deal.title}
                      </p>
                      <p className="text-[10px] text-gray-400 mt-0.5">
                        {deal.sale_price.toLocaleString()}원 · -{Math.round(deal.discount_rate)}%
                      </p>
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <span className={`text-[9px] px-1.5 py-0.5 rounded font-medium ${SOURCE_COLOR[deal.source] || "bg-gray-100 text-gray-500"}`}>
                        {deal.source}
                      </span>
                      <span className="text-xs font-bold text-gray-700">
                        {deal.clicks_today}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 소스별 현황 (유입경로 대체) */}
        <div className="bg-white border border-gray-200 p-5">
          <h2 className="text-sm font-bold text-gray-900 mb-3 pb-2 border-b border-gray-100">
            딜 소스 현황
          </h2>
          <SourceBreakdown top10={metrics.top10} activeDeals={metrics.today.active_deals} />
        </div>
      </div>
    </div>
  );
}

/* ── 소스 현황 ── */
function SourceBreakdown({
  top10,
  activeDeals,
}: {
  top10: AdminMetrics["top10"];
  activeDeals: number;
}) {
  const sources = [
    { key: "naver",     label: "네이버",    color: "#00C73C" },
    { key: "coupang",   label: "쿠팡",      color: "#E31E24" },
    { key: "community", label: "커뮤니티",  color: "#2563eb" },
    { key: "admin",     label: "수동등록",  color: "#6b7280" },
  ];

  const clicksBySource: Record<string, number> = {};
  top10.forEach((d) => {
    clicksBySource[d.source] = (clicksBySource[d.source] || 0) + d.clicks_today;
  });
  const totalClicks = Object.values(clicksBySource).reduce((s, v) => s + v, 0) || 1;

  return (
    <div className="space-y-3">
      <p className="text-[10px] text-gray-400 mb-4">오늘 Top 클릭 기준 소스 비율</p>
      {sources.map(({ key, label, color }) => {
        const cnt = clicksBySource[key] || 0;
        const pct = Math.round((cnt / totalClicks) * 100);
        return (
          <div key={key}>
            <div className="flex justify-between text-xs mb-1">
              <span className="font-medium text-gray-700">{label}</span>
              <span className="text-gray-500">{pct}%</span>
            </div>
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pct}%`, backgroundColor: color }}
              />
            </div>
          </div>
        );
      })}

      <div className="pt-3 border-t border-gray-100 mt-3">
        <p className="text-[10px] text-gray-400">활성 딜</p>
        <p className="text-2xl font-black text-gray-900 mt-1">
          {activeDeals}
          <span className="text-sm font-normal text-gray-400 ml-1">개</span>
        </p>
      </div>
    </div>
  );
}
