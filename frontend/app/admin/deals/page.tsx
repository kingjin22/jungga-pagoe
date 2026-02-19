"use client";

import { useEffect, useState, useCallback } from "react";
import {
  getAdminDeals,
  patchAdminDeal,
  rescrapeAdminDeal,
  AdminDeal,
  AdminDealsResponse,
} from "@/lib/admin-api";

const STATUS_LABELS: Record<string, string> = {
  active: "활성",
  expired: "만료",
  price_changed: "가격변동",
  pending: "대기",
};

const STATUS_COLORS: Record<string, string> = {
  active: "text-green-600 bg-green-50",
  expired: "text-gray-400 bg-gray-100",
  price_changed: "text-amber-600 bg-amber-50",
  pending: "text-blue-600 bg-blue-50",
};

const SOURCE_LABELS: Record<string, string> = {
  naver: "네이버",
  coupang: "쿠팡",
  community: "커뮤니티",
};

function formatPrice(p: number) {
  return p.toLocaleString("ko-KR") + "원";
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const h = Math.floor(diff / 3600000);
  if (h < 1) return "방금";
  if (h < 24) return `${h}시간 전`;
  return `${Math.floor(h / 24)}일 전`;
}

export default function AdminDealsPage() {
  const [data, setData] = useState<AdminDealsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // filters
  const [status, setStatus] = useState("");
  const [source, setSource] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("latest");
  const [page, setPage] = useState(1);

  // patch modal
  const [editing, setEditing] = useState<AdminDeal | null>(null);
  const [patchLoading, setPatchLoading] = useState(false);
  const [noteInput, setNoteInput] = useState("");
  const [statusInput, setStatusInput] = useState("");
  const [pinnedInput, setPinnedInput] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getAdminDeals({
        status: status || undefined,
        source: source || undefined,
        search: search || undefined,
        sort,
        page,
        size: 30,
      });
      setData(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "오류 발생");
    } finally {
      setLoading(false);
    }
  }, [status, source, search, sort, page]);

  useEffect(() => {
    load();
  }, [load]);

  const openEdit = (deal: AdminDeal) => {
    setEditing(deal);
    setNoteInput(deal.admin_note || "");
    setStatusInput(deal.status);
    setPinnedInput(deal.pinned ?? false);
  };

  const saveEdit = async () => {
    if (!editing) return;
    setPatchLoading(true);
    try {
      await patchAdminDeal(editing.id, {
        status: statusInput,
        pinned: pinnedInput,
        admin_note: noteInput || undefined,
      });
      setEditing(null);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "저장 실패");
    } finally {
      setPatchLoading(false);
    }
  };

  const handleRescrape = async (deal: AdminDeal) => {
    try {
      const res = await rescrapeAdminDeal(deal.id);
      alert(res.status === "rescrape_queued" ? "재수집 예약됨" : res.message || res.status);
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "재수집 실패");
    }
  };

  const handleQuickStatus = async (deal: AdminDeal, newStatus: string) => {
    try {
      await patchAdminDeal(deal.id, { status: newStatus });
      load();
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="p-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-black text-gray-900">딜 관리</h1>
          {data && (
            <p className="text-sm text-gray-400 mt-0.5">
              총 {data.total.toLocaleString()}건
            </p>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-2 mb-5">
        <input
          type="text"
          placeholder="제목 검색..."
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          className="border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:border-gray-900 w-52"
        />
        <select
          value={status}
          onChange={(e) => { setStatus(e.target.value); setPage(1); }}
          className="border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:border-gray-900 bg-white"
        >
          <option value="">전체 상태</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          value={source}
          onChange={(e) => { setSource(e.target.value); setPage(1); }}
          className="border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:border-gray-900 bg-white"
        >
          <option value="">전체 소스</option>
          {Object.entries(SOURCE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          value={sort}
          onChange={(e) => { setSort(e.target.value); setPage(1); }}
          className="border border-gray-200 px-3 py-1.5 text-sm focus:outline-none focus:border-gray-900 bg-white"
        >
          <option value="latest">최신순</option>
          <option value="popular">인기순</option>
          <option value="discount">할인율순</option>
          <option value="views">조회순</option>
        </select>
        <button
          onClick={load}
          className="border border-gray-200 px-3 py-1.5 text-sm font-medium hover:border-gray-900 transition-colors"
        >
          새로고침
        </button>
      </div>

      {error && (
        <div className="mb-4 text-sm text-[#E31E24]">{error}</div>
      )}

      {loading ? (
        <div className="text-sm text-gray-400">로딩 중...</div>
      ) : (
        <>
          {/* Table */}
          <div className="bg-white border border-gray-200 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-8">
                    ID
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                    제목
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-20">
                    가격
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-16">
                    할인
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-16">
                    소스
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-20">
                    상태
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-16">
                    조회
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-16">
                    추천
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-20">
                    등록
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-28">
                    액션
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(data?.items || []).map((deal) => (
                  <tr key={deal.id} className={`hover:bg-gray-50 ${deal.pinned ? "bg-yellow-50" : ""}`}>
                    <td className="px-4 py-3 text-xs text-gray-400">
                      {deal.id}
                      {deal.pinned && <span className="ml-1 text-yellow-500">📌</span>}
                    </td>
                    <td className="px-4 py-3">
                      <p className="text-xs font-medium text-gray-800 line-clamp-2 max-w-xs">
                        {deal.title}
                      </p>
                      {deal.admin_note && (
                        <p className="text-[10px] text-purple-500 mt-0.5">
                          📝 {deal.admin_note}
                        </p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-700">
                      {formatPrice(deal.sale_price)}
                    </td>
                    <td className="px-4 py-3 text-xs font-bold text-[#E31E24]">
                      {deal.discount_rate > 0 ? `-${Math.round(deal.discount_rate)}%` : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {SOURCE_LABELS[deal.source] || deal.source}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${
                          STATUS_COLORS[deal.status] || "text-gray-500 bg-gray-100"
                        }`}
                      >
                        {STATUS_LABELS[deal.status] || deal.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {(deal.views ?? 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {deal.upvotes}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-400">
                      {timeAgo(deal.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <button
                          onClick={() => openEdit(deal)}
                          className="text-[10px] font-medium text-gray-600 hover:text-gray-900 border border-gray-200 px-2 py-0.5 hover:border-gray-900 transition-colors"
                        >
                          편집
                        </button>
                        {deal.status === "active" && (
                          <button
                            onClick={() => handleQuickStatus(deal, "expired")}
                            className="text-[10px] font-medium text-gray-400 hover:text-[#E31E24] border border-gray-200 px-2 py-0.5 hover:border-[#E31E24] transition-colors"
                          >
                            만료
                          </button>
                        )}
                        {deal.source === "naver" && (
                          <button
                            onClick={() => handleRescrape(deal)}
                            className="text-[10px] font-medium text-blue-500 hover:text-blue-700 border border-blue-200 px-2 py-0.5 hover:border-blue-700 transition-colors"
                          >
                            재수집
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {(!data?.items || data.items.length === 0) && (
              <div className="py-12 text-center text-sm text-gray-400">
                딜이 없습니다.
              </div>
            )}
          </div>

          {/* Pagination */}
          {data && data.pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-4">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-3 py-1.5 text-sm border border-gray-200 disabled:opacity-40 hover:border-gray-900 transition-colors"
              >
                이전
              </button>
              <span className="text-sm text-gray-500">
                {page} / {data.pages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                disabled={page >= data.pages}
                className="px-3 py-1.5 text-sm border border-gray-200 disabled:opacity-40 hover:border-gray-900 transition-colors"
              >
                다음
              </button>
            </div>
          )}
        </>
      )}

      {/* Edit Modal */}
      {editing && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
          onClick={() => setEditing(null)}
        >
          <div
            className="bg-white w-full max-w-md p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-base font-bold text-gray-900 mb-4">
              딜 편집 #{editing.id}
            </h2>
            <p className="text-xs text-gray-500 mb-4 line-clamp-2">
              {editing.title}
            </p>

            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1 uppercase tracking-wider">
                  상태
                </label>
                <select
                  value={statusInput}
                  onChange={(e) => setStatusInput(e.target.value)}
                  className="w-full border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-gray-900 bg-white"
                >
                  {Object.entries(STATUS_LABELS).map(([k, v]) => (
                    <option key={k} value={k}>{v}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1 uppercase tracking-wider">
                  고정 (핀)
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={pinnedInput}
                    onChange={(e) => setPinnedInput(e.target.checked)}
                    id="pinned-cb"
                    className="w-4 h-4"
                  />
                  <label htmlFor="pinned-cb" className="text-sm text-gray-600">
                    상단 고정
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-600 mb-1 uppercase tracking-wider">
                  관리자 메모
                </label>
                <textarea
                  value={noteInput}
                  onChange={(e) => setNoteInput(e.target.value)}
                  className="w-full border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-gray-900 resize-none"
                  rows={3}
                  placeholder="내부 메모 (사용자에게 노출되지 않음)"
                />
              </div>
            </div>

            <div className="flex gap-2 mt-6">
              <button
                onClick={saveEdit}
                disabled={patchLoading}
                className="flex-1 bg-[#111] text-white font-bold py-2.5 text-sm hover:bg-[#333] transition-colors disabled:opacity-40"
              >
                {patchLoading ? "저장 중..." : "저장"}
              </button>
              <button
                onClick={() => setEditing(null)}
                className="flex-1 border border-gray-200 font-bold py-2.5 text-sm hover:border-gray-900 transition-colors"
              >
                취소
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
