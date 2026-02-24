"use client";

import { useState, useCallback, useEffect } from "react";
import { Deal } from "@/lib/api";
import DealCard from "./DealCard";
import DealModal from "./DealModal";

const STORAGE_KEY = "dismissed_deal_ids";

function loadDismissed(): Set<number> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? new Set(JSON.parse(raw) as number[]) : new Set();
  } catch {
    return new Set();
  }
}

function saveDismissed(ids: Set<number>) {
  try {
    // 최대 200개까지만 저장 (오래된 것 자동 제거)
    const arr = Array.from(ids).slice(-200);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(arr));
  } catch {}
}

export default function DealGrid({ deals }: { deals: Deal[] }) {
  const [selectedDeal, setSelectedDeal] = useState<Deal | null>(null);
  const [dismissed, setDismissed] = useState<Set<number>>(new Set());

  useEffect(() => {
    setDismissed(loadDismissed());
  }, []);

  const handleClose = useCallback(() => setSelectedDeal(null), []);

  const handleDismiss = useCallback((dealId: number) => {
    setDismissed((prev) => {
      const next = new Set(prev);
      next.add(dealId);
      saveDismissed(next);
      return next;
    });
  }, []);

  const visible = deals.filter((d) => !dismissed.has(d.id));

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-x-4 gap-y-8">
        {visible.map((deal) => (
          <DealCard
            key={deal.id}
            deal={deal}
            onClick={setSelectedDeal}
            onDismiss={handleDismiss}
          />
        ))}
      </div>
      {dismissed.size > 0 && (
        <p className="text-xs text-center text-gray-300 mt-4">
          {dismissed.size}개 딜 숨김 ·{" "}
          <button
            className="underline hover:text-gray-500"
            onClick={() => {
              setDismissed(new Set());
              localStorage.removeItem(STORAGE_KEY);
            }}
          >
            초기화
          </button>
        </p>
      )}
      <DealModal deal={selectedDeal} onClose={handleClose} />
    </>
  );
}
