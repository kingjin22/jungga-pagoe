"use client";

import { useState, useEffect } from "react";

const STORAGE_KEY = "purchased_deals";

function getPurchasedDeals(): number[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function savePurchasedDeals(ids: number[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // localStorage unavailable (private mode, etc.) — silently ignore
  }
}

export default function BoughtButton({ dealId }: { dealId: number }) {
  const [bought, setBought] = useState(false);
  const [bounce, setBounce] = useState(false);

  // SSR-safe: localStorage is only read after mount
  useEffect(() => {
    const ids = getPurchasedDeals();
    setBought(ids.includes(dealId));
  }, [dealId]);

  function handleClick() {
    const ids = getPurchasedDeals();
    let next: number[];
    if (ids.includes(dealId)) {
      next = ids.filter((id) => id !== dealId);
    } else {
      next = [...ids, dealId];
    }
    savePurchasedDeals(next);
    setBought(next.includes(dealId));

    // Scale bounce animation
    setBounce(true);
    setTimeout(() => setBounce(false), 300);
  }

  return (
    <button
      onClick={handleClick}
      aria-label={bought ? "구매 취소" : "구매했어요"}
      title={bought ? "구매 취소하기" : "구매했어요"}
      className={[
        "w-full py-3 text-base font-bold transition-all duration-200",
        bounce ? "scale-95" : "scale-100",
        bought
          ? "bg-emerald-600 hover:bg-emerald-700 text-white"
          : "bg-indigo-700 hover:bg-indigo-800 text-white",
      ].join(" ")}
    >
      {bought ? "✅ 구매완료" : "🛒 구매했어요"}
    </button>
  );
}
