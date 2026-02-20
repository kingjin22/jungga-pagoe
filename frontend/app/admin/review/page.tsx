"use client";

import { useEffect, useState } from "react";
import { getPendingDeals, approveDeal, rejectDeal, AdminDeal } from "@/lib/admin-api";

const STATUS_LABEL: Record<string, { label: string; color: string }> = {
  pending: { label: "검토 대기", color: "bg-yellow-100 text-yellow-800" },
  rejected: { label: "거부됨", color: "bg-red-100 text-red-700" },
};

function VerifyBadge({ note }: { note?: string }) {
  if (!note) return null;
  if (note.includes("✅ 자동 검증 통과"))
    return <span className="text-xs text-green-600 font-medium">✅ 자동검증 통과</span>;
  if (note.includes("❌ 자동 거부"))
    return <span className="text-xs text-red-500 font-medium">❌ 가격 불일치</span>;
  if (note.includes("⚠️"))
    return <span className="text-xs text-yellow-600 font-medium">⚠️ 수동 확인 필요</span>;
  return null;
}

export default function ReviewPage() {
  const [deals, setDeals] = useState<AdminDeal[]>([]);
  const [loading, setLoading] = useState(true);
  const [rejectInput, setRejectInput] = useState<Record<number, string>>({});
  const [processing, setProcessing] = useState<number | null>(null);

  const load = () => {
    getPendingDeals()
      .then((r) => setDeals(r.deals))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const pending = deals.filter((d) => d.status === "pending");
  const rejected = deals.filter((d) => d.status === "rejected");

  const handleApprove = async (id: number) => {
    setProcessing(id);
    try {
      await approveDeal(id);
      load();
    } catch (e: unknown) {
      alert((e as Error).message || "승인 실패");
    } finally {
      setProcessing(null);
    }
  };

  const handleReject = async (id: number) => {
    setProcessing(id);
    try {
      await rejectDeal(id, rejectInput[id] || "사유 미입력");
      load();
    } catch (e: unknown) {
      alert((e as Error).message || "거부 실패");
    } finally {
      setProcessing(null);
    }
  };

  if (loading) return <div className="p-8 text-sm text-gray-400">로딩 중...</div>;

  return (
    <div className="p-8 max-w-5xl">
      <div className="mb-6">
        <h1 className="text-xl font-black text-gray-900">제보 검토</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          대기 <span className="font-bold text-gray-700">{pending.length}건</span>
          {" · "}거부됨 <span className="font-bold text-gray-500">{rejected.length}건</span>
        </p>
      </div>

      {pending.length === 0 && (
        <div className="border border-gray-200 bg-white p-10 text-center text-sm text-gray-400">
          검토 대기 중인 제보가 없습니다
        </div>
      )}

      {/* 대기 목록 */}
      {pending.length > 0 && (
        <div className="space-y-3 mb-10">
          <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider">대기</h2>
          {pending.map((deal) => (
            <DealReviewCard
              key={deal.id}
              deal={deal}
              onApprove={() => handleApprove(deal.id)}
              onReject={() => handleReject(deal.id)}
              rejectReason={rejectInput[deal.id] || ""}
              onReasonChange={(v) => setRejectInput((p) => ({ ...p, [deal.id]: v }))}
              processing={processing === deal.id}
            />
          ))}
        </div>
      )}

      {/* 거부 내역 */}
      {rejected.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider">거부됨 (최근 100건)</h2>
          {rejected.map((deal) => (
            <div key={deal.id} className="border border-gray-100 bg-white p-4 flex items-center gap-4 opacity-60">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-700 truncate">{deal.title}</p>
                <p className="text-xs text-gray-400 mt-0.5">{deal.admin_note}</p>
              </div>
              <div className="text-xs text-gray-400">{new Date(deal.created_at).toLocaleDateString("ko-KR")}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DealReviewCard({
  deal,
  onApprove,
  onReject,
  rejectReason,
  onReasonChange,
  processing,
}: {
  deal: AdminDeal;
  onApprove: () => void;
  onReject: () => void;
  rejectReason: string;
  onReasonChange: (v: string) => void;
  processing: boolean;
}) {
  const dr = deal.original_price > 0
    ? Math.round((1 - deal.sale_price / deal.original_price) * 100)
    : 0;

  return (
    <div className="border border-gray-200 bg-white p-5">
      <div className="flex items-start gap-4">
        {/* 이미지 */}
        {deal.image_url && (
          <img src={deal.image_url} alt="" className="w-16 h-16 object-cover border border-gray-100 shrink-0" />
        )}

        {/* 정보 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <VerifyBadge note={deal.admin_note} />
            <span className="text-xs text-gray-400">제보자: {deal.submitter_name}</span>
          </div>
          <p className="font-bold text-gray-900 text-sm">{deal.title}</p>
          <div className="flex items-center gap-3 mt-1">
            <span className="text-xs text-gray-400 line-through">{deal.original_price.toLocaleString()}원</span>
            <span className="text-base font-black text-[#E31E24]">{deal.sale_price.toLocaleString()}원</span>
            <span className="text-xs font-bold text-[#E31E24]">-{dr}%</span>
          </div>
          <a
            href={deal.product_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-500 hover:underline mt-1 block truncate"
          >
            {deal.product_url}
          </a>
          {deal.admin_note && (
            <p className="text-xs text-gray-400 mt-2 border-l-2 border-gray-200 pl-2 whitespace-pre-line">
              {deal.admin_note}
            </p>
          )}
        </div>

        {/* 날짜 */}
        <div className="text-xs text-gray-400 shrink-0">
          {new Date(deal.created_at).toLocaleString("ko-KR", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>

      {/* 액션 */}
      <div className="mt-4 flex items-center gap-2">
        <button
          onClick={onApprove}
          disabled={processing}
          className="px-4 py-2 bg-gray-900 text-white text-sm font-bold hover:bg-black disabled:opacity-40 transition-colors"
        >
          {processing ? "처리 중..." : "✅ 승인"}
        </button>
        <input
          type="text"
          placeholder="거부 사유 (선택)"
          value={rejectReason}
          onChange={(e) => onReasonChange(e.target.value)}
          className="flex-1 border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:border-gray-400"
        />
        <button
          onClick={onReject}
          disabled={processing}
          className="px-4 py-2 border border-gray-300 text-gray-600 text-sm font-bold hover:bg-gray-50 disabled:opacity-40 transition-colors"
        >
          ❌ 거부
        </button>
      </div>
    </div>
  );
}
