"use client";
import { useEffect, useState, useCallback } from "react";

const KEY = "jungga_favorites";
const MAX = 100;

export function useFavorites() {
  const [ids, setIds] = useState<Set<number>>(new Set());

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(KEY) || "[]");
      setIds(new Set(saved));
    } catch {}
  }, []);

  const toggle = useCallback((id: number) => {
    setIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        if (next.size >= MAX) {
          // 가장 오래된 항목 제거 (첫 번째)
          next.delete(next.values().next().value!);
        }
        next.add(id);
      }
      localStorage.setItem(KEY, JSON.stringify([...next]));
      return next;
    });
  }, []);

  const isFav = useCallback((id: number) => ids.has(id), [ids]);
  const favIds = [...ids];

  return { toggle, isFav, favIds, count: ids.size };
}
