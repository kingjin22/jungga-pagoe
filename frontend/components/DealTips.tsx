"use client";

import { useState, useEffect, useCallback } from "react";

// C-012: 딜 꿀팁 댓글 기능 (localStorage 기반)
interface Tip {
  id: string;
  text: string;
  createdAt: number;
}

interface DealTipsProps {
  dealId: number | string;
}

const MAX_TIPS = 10;

function formatRelativeTime(ts: number): string {
  const diffMs = Date.now() - ts;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays > 0) return `${diffDays}일 전`;
  if (diffHours > 0) return `${diffHours}시간 전`;
  if (diffMins > 0) return `${diffMins}분 전`;
  return "방금 전";
}

export default function DealTips({ dealId }: DealTipsProps) {
  const storageKey = `tips_${dealId}`;
  const [tips, setTips] = useState<Tip[]>([]);
  const [inputText, setInputText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [mounted, setMounted] = useState(false);

  const loadTips = useCallback(() => {
    if (typeof window === "undefined") return;
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) {
        const parsed = JSON.parse(raw) as Tip[];
        setTips(Array.isArray(parsed) ? parsed : []);
      } else {
        setTips([]);
      }
    } catch {
      setTips([]);
    }
  }, [storageKey]);

  useEffect(() => {
    setMounted(true);
    loadTips();
  }, [loadTips]);

  const handleSubmit = () => {
    const trimmed = inputText.trim();
    if (!trimmed || trimmed.length < 2) return;

    setIsSubmitting(true);

    const newTip: Tip = {
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      text: trimmed,
      createdAt: Date.now(),
    };

    setTips((prev) => {
      // 최신 순으로 앞에 추가, 최대 10개 유지 (오래된 것 삭제)
      const updated = [newTip, ...prev].slice(0, MAX_TIPS);
      try {
        localStorage.setItem(storageKey, JSON.stringify(updated));
      } catch {
        // localStorage quota exceeded — ignore
      }
      return updated;
    });

    setInputText("");

    setTimeout(() => setIsSubmitting(false), 300);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const placeholders = [
    "네이버페이로 결제하면 5% 추가 적립돼요!",
    "쿠팡에서 찾으면 더 쌀 수도 있어요",
    "할인코드나 추가 혜택 공유해주세요 🙌",
  ];

  const placeholder = placeholders[Number(dealId) % placeholders.length] ?? placeholders[0];

  // SSR hydration mismatch 방지 — 마운트 전에는 스켈레톤 노출 안함
  if (!mounted) return null;

  return (
    <section className="mt-10 border-t border-gray-100 pt-6">
      <h2 className="text-[15px] font-bold text-gray-900 mb-4 flex items-center gap-2">
        💡 꿀팁 남기기
        {tips.length > 0 && (
          <span className="text-[12px] font-normal text-gray-400">({tips.length}개)</span>
        )}
      </h2>

      {/* 입력창 */}
      <div className="flex gap-2 mb-5">
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          maxLength={200}
          className="flex-1 text-sm border border-gray-200 px-3 py-2.5 rounded-sm focus:outline-none focus:border-gray-400 text-gray-800 placeholder-gray-300"
        />
        <button
          onClick={handleSubmit}
          disabled={isSubmitting || inputText.trim().length < 2}
          className="px-4 py-2.5 bg-gray-900 text-white text-sm font-semibold rounded-sm hover:bg-black transition-colors disabled:opacity-40 disabled:cursor-not-allowed whitespace-nowrap"
        >
          등록
        </button>
      </div>

      {/* 꿀팁 목록 */}
      {tips.length === 0 ? (
        <div className="text-center py-8 text-gray-300">
          <p className="text-3xl mb-2">💬</p>
          <p className="text-sm">첫 번째 꿀팁을 남겨보세요!</p>
        </div>
      ) : (
        <ul className="space-y-2.5">
          {tips.map((tip) => (
            <li
              key={tip.id}
              className="bg-yellow-50 border border-yellow-100 rounded-sm px-3.5 py-3 flex items-start gap-2.5"
            >
              <span className="text-base mt-0.5 shrink-0">💡</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-800 leading-snug break-words">{tip.text}</p>
                <p className="text-[11px] text-gray-400 mt-1">{formatRelativeTime(tip.createdAt)}</p>
              </div>
            </li>
          ))}
        </ul>
      )}

      <p className="text-[11px] text-gray-300 mt-3">
        꿀팁은 이 기기에만 저장돼요 · 최대 {MAX_TIPS}개
      </p>
    </section>
  );
}
