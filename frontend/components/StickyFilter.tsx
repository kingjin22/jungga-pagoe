"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CategoryItem } from "@/lib/api";

export default function StickyFilter({ categories }: { categories: CategoryItem[] }) {
  const [sticky, setSticky] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const current = searchParams.get("category") || "";

  useEffect(() => {
    const onScroll = () => setSticky(window.scrollY > 120);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleCategory = (cat: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (cat === "" || cat === current) {
      params.delete("category");
    } else {
      params.set("category", cat);
    }
    params.set("page", "1");
    router.push(`/?${params.toString()}`);
  };

  if (categories.length === 0) return null;

  return (
    <div
      className={`bg-white z-40 transition-shadow ${
        sticky
          ? "fixed top-0 left-0 right-0 shadow-sm border-b border-gray-200 px-4 py-2"
          : "relative py-3 border-b border-gray-100"
      }`}
    >
      <div className={`${sticky ? "max-w-screen-xl mx-auto" : ""} flex gap-2 overflow-x-auto scrollbar-hide`}>
        <button
          onClick={() => handleCategory("")}
          className={`shrink-0 text-xs px-3 py-1.5 border transition-colors ${
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
            onClick={() => handleCategory(category)}
            className={`shrink-0 text-xs px-3 py-1.5 border transition-colors ${
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
    </div>
  );
}
