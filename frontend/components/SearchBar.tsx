"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";

interface Suggestion {
  type: "brand" | "category" | "title";
  value: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";

const TYPE_LABEL: Record<Suggestion["type"], string> = {
  brand: "브랜드",
  category: "카테고리",
  title: "제품",
};

interface SearchBarProps {
  onClose?: () => void;
}

export default function SearchBar({ onClose }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const router = useRouter();

  const fetchSuggestions = useCallback(async (q: string) => {
    if (q.length < 1) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    try {
      const res = await fetch(
        `${API_BASE}/api/deals/suggestions?q=${encodeURIComponent(q)}`
      );
      if (!res.ok) return;
      const data: Suggestion[] = await res.json();
      setSuggestions(data);
      setOpen(data.length > 0);
      setActiveIndex(-1);
    } catch {
      // network error — silent
    }
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(query), 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, fetchSuggestions]);

  // Close on outside click
  useEffect(() => {
    const handleMouseDown = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, []);

  const executeSearch = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    setOpen(false);
    setSuggestions([]);
    setQuery("");
    router.push(`/?search=${encodeURIComponent(trimmed)}`);
    onClose?.();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const target = activeIndex >= 0 ? suggestions[activeIndex]?.value : query;
    executeSearch(target || query);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => Math.max(prev - 1, -1));
    } else if (e.key === "Escape") {
      setOpen(false);
      setActiveIndex(-1);
    }
  };

  return (
    <div ref={containerRef} className="relative flex-1">
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          placeholder="브랜드, 카테고리, 제품명 검색..."
          autoFocus
          className="flex-1 bg-[#222] text-white placeholder-gray-500 px-4 py-2 text-sm border border-gray-600 focus:border-gray-400 outline-none"
        />
        <button
          type="submit"
          className="bg-white text-black px-5 py-2 text-sm font-semibold hover:bg-gray-100 transition-colors"
        >
          검색
        </button>
      </form>

      {open && suggestions.length > 0 && (
        <ul className="absolute top-full left-0 right-0 z-50 bg-[#1a1a1a] border border-gray-700 shadow-lg mt-0.5 max-h-64 overflow-y-auto">
          {suggestions.slice(0, 6).map((s, i) => (
            <li key={`${s.type}-${s.value}`}>
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  executeSearch(s.value);
                }}
                onMouseEnter={() => setActiveIndex(i)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-sm text-left transition-colors ${
                  i === activeIndex
                    ? "bg-[#333] text-white"
                    : "text-gray-300 hover:bg-[#2a2a2a]"
                }`}
              >
                <span className="text-[10px] font-bold uppercase tracking-wider text-gray-500 w-14 shrink-0">
                  {TYPE_LABEL[s.type]}
                </span>
                <span className="truncate">{s.value}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
