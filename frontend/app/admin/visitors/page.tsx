"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";
const ADMIN_KEY = "jungga2026admin";

function timeKST(iso: string) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("ko-KR", {
    timeZone: "Asia/Seoul",
    month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

function DeviceBadge({ device }: { device: string }) {
  const colors: Record<string, string> = {
    "PC": "bg-blue-100 text-blue-700",
    "모바일": "bg-green-100 text-green-700",
    "봇": "bg-gray-100 text-gray-500",
  };
  return (
    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${colors[device] || "bg-gray-100 text-gray-500"}`}>
      {device}
    </span>
  );
}

export default function VisitorsPage() {
  const [data, setData] = useState<any>(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"summary" | "logs">("summary");

  const load = async (d: number) => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/admin/visitors?days=${d}`, {
        headers: { "X-Admin-Key": ADMIN_KEY },
      });
      setData(await res.json());
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(days); }, [days]);

  return (
    <div className="p-6 max-w-5xl">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-lg font-black text-gray-900">방문자 분석</h1>
          <p className="text-xs text-gray-400 mt-0.5">IP별 방문·클릭 통계</p>
        </div>
        <div className="flex gap-1">
          {[1, 3, 7, 14, 30].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1.5 text-xs font-medium border transition-colors ${
                days === d
                  ? "bg-gray-900 text-white border-gray-900"
                  : "bg-white text-gray-500 border-gray-200 hover:border-gray-400"
              }`}
            >
              {d}일
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-sm text-gray-400 py-8">불러오는 중...</div>
      ) : !data ? (
        <div className="text-sm text-red-500">데이터 없음</div>
      ) : (
        <>
          {/* 요약 카드 */}
          <div className="grid grid-cols-3 gap-3 mb-6">
            {[
              { label: "고유 IP", value: data.total_ips },
              { label: "총 딜 오픈", value: data.summary.reduce((s: number, r: any) => s + r.deal_opens, 0) },
              { label: "총 구매 클릭", value: data.summary.reduce((s: number, r: any) => s + r.clicks, 0) },
            ].map(({ label, value }) => (
              <div key={label} className="border border-gray-200 p-4 bg-white">
                <p className="text-xs text-gray-400 mb-1">{label}</p>
                <p className="text-2xl font-black text-gray-900">{value.toLocaleString()}</p>
              </div>
            ))}
          </div>

          {/* 탭 */}
          <div className="flex border-b border-gray-200 mb-4">
            {(["summary", "logs"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  tab === t ? "border-gray-900 text-gray-900" : "border-transparent text-gray-400 hover:text-gray-700"
                }`}
              >
                {t === "summary" ? "IP별 요약" : "최근 로그"}
              </button>
            ))}
          </div>

          {/* IP별 요약 테이블 */}
          {tab === "summary" && (
            <div className="bg-white border border-gray-200 overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-4 py-2.5 font-semibold text-gray-500">IP</th>
                    <th className="text-center px-3 py-2.5 font-semibold text-gray-500">기기</th>
                    <th className="text-center px-3 py-2.5 font-semibold text-gray-500">방문</th>
                    <th className="text-center px-3 py-2.5 font-semibold text-gray-500">딜 오픈</th>
                    <th className="text-center px-3 py-2.5 font-semibold text-gray-500">구매 클릭</th>
                    <th className="text-center px-3 py-2.5 font-semibold text-gray-500">세션</th>
                    <th className="text-left px-3 py-2.5 font-semibold text-gray-500">첫 방문</th>
                    <th className="text-left px-3 py-2.5 font-semibold text-gray-500">마지막</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.summary.map((row: any, i: number) => (
                    <tr key={i} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-2.5 font-mono text-gray-800">{row.ip}</td>
                      <td className="px-3 py-2.5 text-center"><DeviceBadge device={row.device} /></td>
                      <td className="px-3 py-2.5 text-center font-medium text-gray-700">{row.visits}</td>
                      <td className="px-3 py-2.5 text-center font-medium text-gray-700">{row.deal_opens}</td>
                      <td className={`px-3 py-2.5 text-center font-bold ${row.clicks > 0 ? "text-[#E31E24]" : "text-gray-300"}`}>
                        {row.clicks}
                      </td>
                      <td className="px-3 py-2.5 text-center text-gray-500">{row.sessions}</td>
                      <td className="px-3 py-2.5 text-gray-400">{timeKST(row.first_seen)}</td>
                      <td className="px-3 py-2.5 text-gray-400">{timeKST(row.last_seen)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {data.summary.length === 0 && (
                <p className="text-center text-sm text-gray-400 py-8">
                  데이터 없음 — IP 컬럼이 추가됐는지 확인하세요
                </p>
              )}
            </div>
          )}

          {/* 최근 이벤트 로그 */}
          {tab === "logs" && (
            <div className="bg-white border border-gray-200 overflow-hidden">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-200">
                    <th className="text-left px-4 py-2.5 font-semibold text-gray-500">시각 (KST)</th>
                    <th className="text-left px-3 py-2.5 font-semibold text-gray-500">IP</th>
                    <th className="text-center px-3 py-2.5 font-semibold text-gray-500">이벤트</th>
                    <th className="text-center px-3 py-2.5 font-semibold text-gray-500">딜 ID</th>
                    <th className="text-center px-3 py-2.5 font-semibold text-gray-500">기기</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {data.recent_logs.map((log: any, i: number) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-gray-500">{timeKST(log.time)}</td>
                      <td className="px-3 py-2 font-mono text-gray-700">{log.ip}</td>
                      <td className="px-3 py-2 text-center">
                        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                          log.event === "outbound_click" ? "bg-red-100 text-red-700" :
                          log.event === "deal_open" ? "bg-blue-100 text-blue-700" :
                          "bg-gray-100 text-gray-500"
                        }`}>
                          {log.event === "outbound_click" ? "구매클릭" :
                           log.event === "deal_open" ? "딜오픈" : "방문"}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-center text-gray-400">
                        {log.deal_id ? `#${log.deal_id}` : "-"}
                      </td>
                      <td className="px-3 py-2 text-center"><DeviceBadge device={log.device} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
