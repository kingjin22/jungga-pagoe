"use client";
import { useEffect, useState, useCallback } from "react";

const KEY = "jungga_recent";
const MAX = 8;

export function useRecentDeals() {
  const [recentIds, setRecentIds] = useState<number[]>([]);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(KEY) || "[]");
      setRecentIds(saved);
    } catch {}
  }, []);

  const addRecent = useCallback((id: number) => {
    setRecentIds(prev => {
      const next = [id, ...prev.filter(x => x !== id)].slice(0, MAX);
      localStorage.setItem(KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  return { recentIds, addRecent };
}
