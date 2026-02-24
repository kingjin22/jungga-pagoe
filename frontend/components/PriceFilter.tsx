"use client";
import { useRouter, useSearchParams, usePathname } from "next/navigation";

const PRICE_OPTIONS = [
  { label: "전체", min: null, max: null },
  { label: "5만 이하", min: null, max: 50000 },
  { label: "5~20만", min: 50000, max: 200000 },
  { label: "20만+", min: 200000, max: null },
];

export default function PriceFilter() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentMin = searchParams.get("price_min");
  const currentMax = searchParams.get("price_max");

  const isActive = (min: number | null, max: number | null) => {
    return (
      String(min ?? "") === String(currentMin ?? "") &&
      String(max ?? "") === String(currentMax ?? "")
    );
  };

  const handleSelect = (min: number | null, max: number | null) => {
    const params = new URLSearchParams(searchParams.toString());
    if (min) params.set("price_min", String(min));
    else params.delete("price_min");
    if (max) params.set("price_max", String(max));
    else params.delete("price_max");
    router.push(`${pathname}?${params.toString()}`);
  };

  return (
    <div className="flex gap-2 flex-wrap">
      {PRICE_OPTIONS.map((opt) => (
        <button
          key={opt.label}
          onClick={() => handleSelect(opt.min, opt.max)}
          className={`text-[12px] px-3 py-1.5 border transition-colors ${
            isActive(opt.min, opt.max)
              ? "border-gray-900 bg-gray-900 text-white"
              : "border-gray-200 text-gray-600 hover:border-gray-400"
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
