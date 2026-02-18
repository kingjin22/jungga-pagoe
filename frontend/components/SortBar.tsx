"use client";

import { useRouter, useSearchParams } from "next/navigation";

const SORTS = [
  { value: "latest", label: "⏰ 최신순" },
  { value: "popular", label: "👍 인기순" },
  { value: "discount", label: "🔥 할인율순" },
  { value: "price_asc", label: "💰 가격낮은순" },
  { value: "price_desc", label: "💎 가격높은순" },
];

export default function SortBar({ total }: { total: number }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const currentSort = searchParams.get("sort") || "latest";

  const handleSort = (sort: string) => {
    const params = new URLSearchParams(searchParams.toString());
    params.set("sort", sort);
    params.set("page", "1");
    router.push(`/?${params.toString()}`);
  };

  return (
    <div className="flex items-center justify-between mb-4">
      <p className="text-sm text-gray-500">
        총 <span className="font-bold text-gray-800">{total.toLocaleString()}</span>개 딜
      </p>

      <div className="flex gap-1 overflow-x-auto">
        {SORTS.map((s) => (
          <button
            key={s.value}
            onClick={() => handleSort(s.value)}
            className={`whitespace-nowrap text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
              currentSort === s.value
                ? "bg-[#E31E24] text-white"
                : "bg-white text-gray-600 hover:bg-gray-100 border border-gray-200"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}
