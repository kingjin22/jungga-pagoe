"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

// C-026: 쇼핑몰별 실시간 핫딜 탭 (쿠차 벤치마킹)

export interface MallItem {
  mall: string;
  label: string;
  icon: string;
  count: number;
}

interface MallTabsProps {
  activeMall?: string; // 현재 선택된 쇼핑몰 (없으면 "전체")
  malls?: MallItem[];  // 외부에서 주입 (SSR 용)
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://jungga-pagoe-production.up.railway.app";

export default function MallTabs({ activeMall, malls: propMalls }: MallTabsProps) {
  const router = useRouter();
  const [malls, setMalls] = useState<MallItem[]>(propMalls || []);

  useEffect(() => {
    if (propMalls && propMalls.length > 0) return;
    fetch(`${API_BASE}/api/deals/malls`)
      .then((r) => r.json())
      .then((data: MallItem[]) => setMalls(data))
      .catch(() => {});
  }, [propMalls]);

  if (malls.length === 0) return null;

  const totalCount = malls.reduce((s, m) => s + m.count, 0);

  const handleClick = (mall: string | null) => {
    if (mall === null) {
      router.push("/");
    } else {
      router.push(`/mall/${mall}`);
    }
  };

  const tabBase =
    "flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-full text-xs font-medium transition-all whitespace-nowrap cursor-pointer";
  const tabActive = "bg-gray-900 text-white";
  const tabInactive = "bg-gray-100 text-gray-600 hover:bg-gray-200";

  return (
    <div className="mb-4">
      <p className="text-xs text-gray-400 mb-2 font-medium">🏬 쇼핑몰별</p>
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
        {/* 전체 탭 */}
        <button
          onClick={() => handleClick(null)}
          className={`${tabBase} ${!activeMall ? tabActive : tabInactive}`}
        >
          <span>전체</span>
          <span className="opacity-60">{totalCount.toLocaleString()}</span>
        </button>

        {/* 쇼핑몰 탭 */}
        {malls.map((m) => (
          <button
            key={m.mall}
            onClick={() => handleClick(m.mall)}
            className={`${tabBase} ${activeMall === m.mall ? tabActive : tabInactive}`}
          >
            <span>{m.icon}</span>
            <span>{m.label}</span>
            <span className="opacity-60">{m.count.toLocaleString()}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
