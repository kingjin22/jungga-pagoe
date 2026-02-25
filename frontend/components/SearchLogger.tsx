"use client";

import { useEffect } from "react";
import { logSearch } from "@/lib/tracking";

// C-002: 검색어 서버 로깅 (서버 컴포넌트에서 호출 불가 → 클라이언트 컴포넌트)
export default function SearchLogger({ keyword }: { keyword: string }) {
  useEffect(() => {
    if (keyword && keyword.trim().length >= 1) {
      logSearch(keyword.trim());
    }
  }, [keyword]);

  return null; // UI 없음
}
