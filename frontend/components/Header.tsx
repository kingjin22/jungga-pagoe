"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter, usePathname } from "next/navigation";

const CATEGORIES = [
  { href: "/", label: "전체" },
  { href: "/?source=coupang", label: "쿠팡" },
  { href: "/?source=naver", label: "네이버" },
  { href: "/?source=community", label: "커뮤니티" },
  { href: "/?category=전자기기", label: "전자기기" },
  { href: "/?category=패션", label: "패션" },
  { href: "/?category=식품", label: "식품" },
  { href: "/?category=뷰티", label: "뷰티" },
  { href: "/?category=홈리빙", label: "홈리빙" },
  { href: "/?category=스포츠", label: "스포츠" },
  { href: "/?hot_only=true", label: "HOT딜" },
];

export default function Header() {
  const [search, setSearch] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (search.trim()) {
      router.push(`/?search=${encodeURIComponent(search.trim())}`);
      setSearchOpen(false);
    }
  };

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200">
      {/* 최상단 바 */}
      <div className="bg-[#111] text-white">
        <div className="max-w-screen-xl mx-auto px-4 py-2 flex items-center justify-between">
          {/* 로고 */}
          <Link href="/" className="font-black text-xl tracking-tight text-white">
            정가파괴
          </Link>

          {/* 우측 액션 */}
          <div className="flex items-center gap-4">
            {/* 검색 아이콘 */}
            <button
              onClick={() => setSearchOpen(!searchOpen)}
              className="text-gray-400 hover:text-white transition-colors"
              aria-label="검색"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8" />
                <path d="m21 21-4.35-4.35" />
              </svg>
            </button>

            {/* 딜 제보 */}
            <Link
              href="/submit"
              className="text-xs font-semibold bg-[#E31E24] text-white px-3 py-1.5 hover:bg-[#c01920] transition-colors"
            >
              딜 제보
            </Link>
          </div>
        </div>

        {/* 검색바 (펼침) */}
        {searchOpen && (
          <div className="border-t border-gray-700">
            <form onSubmit={handleSearch} className="max-w-screen-xl mx-auto px-4 py-3 flex gap-2">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="브랜드, 상품명으로 검색"
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
          </div>
        )}
      </div>

      {/* 카테고리 네비 */}
      <div className="bg-white">
        <div className="max-w-screen-xl mx-auto px-4">
          <nav className="flex overflow-x-auto scrollbar-hide">
            {CATEGORIES.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`shrink-0 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  item.label === "HOT딜"
                    ? "text-[#E31E24] border-transparent hover:border-[#E31E24]"
                    : "text-gray-600 border-transparent hover:text-gray-900 hover:border-gray-900"
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </div>
    </header>
  );
}
