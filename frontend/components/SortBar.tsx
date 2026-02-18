"use client";

import { useRouter, useSearchParams } from "next/navigation";

const SORTS = [
  { value: "latest", label: "최신순" },
  { value: "popular", label: "인기순" },
  { value: "discount", label: "할인율순" },
  { value: "price_asc", label: "낮은가격순" },
  { value: "price_desc", label: "높은가격순" },
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
    <div className="flex items-center justify-between py-3 border-b border-gray-200 mb-6">
      <p className="text-sm text-gray-500">
        총 <span className="font-bold text-gray-900">{total.toLocaleString()}</span>개
      </p>

      <div className="flex items-center gap-0">
        {SORTS.map((s, i) => (
          <button
            key={s.value}
            onClick={() => handleSort(s.value)}
            className={`text-xs px-3 py-1 transition-colors border-r border-gray-200 last:border-r-0 ${
              currentSort === s.value
                ? "text-gray-900 font-bold"
                : "text-gray-400 hover:text-gray-700"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>
    </div>
  );
}
