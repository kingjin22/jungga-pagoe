"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { CategoryItem } from "@/lib/api";

export default function CategoryFilter({
  categories,
}: {
  categories: CategoryItem[];
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const current = searchParams.get("category") || "";

  const select = (cat: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (cat === current) {
      params.delete("category");
    } else {
      params.set("category", cat);
    }
    params.set("page", "1");
    router.push(`/?${params.toString()}`);
  };

  if (categories.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 py-4 border-b border-gray-100">
      <button
        onClick={() => select("")}
        className={`text-xs px-3 py-1.5 border transition-colors ${
          !current
            ? "border-gray-900 bg-gray-900 text-white"
            : "border-gray-200 text-gray-500 hover:border-gray-400 hover:text-gray-700"
        }`}
      >
        전체
      </button>
      {categories.map(({ category, count }) => (
        <button
          key={category}
          onClick={() => select(category)}
          className={`text-xs px-3 py-1.5 border transition-colors ${
            current === category
              ? "border-gray-900 bg-gray-900 text-white"
              : "border-gray-200 text-gray-500 hover:border-gray-400 hover:text-gray-700"
          }`}
        >
          {category}
          <span className={`ml-1.5 ${current === category ? "text-gray-300" : "text-gray-400"}`}>
            {count}
          </span>
        </button>
      ))}
    </div>
  );
}
