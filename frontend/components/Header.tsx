"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function Header() {
  const [search, setSearch] = useState("");
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (search.trim()) {
      router.push(`/?search=${encodeURIComponent(search.trim())}`);
    }
  };

  return (
    <header className="bg-[#E31E24] text-white shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3">
        {/* 상단 행: 로고 + 검색 + 버튼 */}
        <div className="flex items-center gap-3">
          {/* 로고 */}
          <Link href="/" className="flex items-center gap-2 shrink-0">
            <span className="text-2xl sm:text-3xl font-black tracking-tighter">
              정가<span className="text-yellow-300">파괴</span>
            </span>
            <span className="hidden sm:inline text-xs bg-yellow-300 text-red-800 font-bold px-1.5 py-0.5 rounded">
              BETA
            </span>
          </Link>

          {/* 검색바 - 모바일에서 전체 너비 */}
          <form onSubmit={handleSearch} className="flex-1">
            <div className="relative">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="딜 검색 (에어팟, 나이키...)"
                className="w-full px-4 py-2 rounded-full text-gray-800 text-sm outline-none pr-10 bg-white"
              />
              <button
                type="submit"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-red-600"
              >
                🔍
              </button>
            </div>
          </form>

          {/* 제보하기 버튼 */}
          <Link
            href="/submit"
            className="shrink-0 bg-yellow-300 text-red-800 font-bold px-3 sm:px-4 py-2 rounded-full text-sm hover:bg-yellow-400 transition-colors"
          >
            <span className="hidden sm:inline">💡 딜 제보</span>
            <span className="sm:hidden">💡</span>
          </Link>
        </div>

        {/* 카테고리 네비 - 가로 스크롤 */}
        <nav className="flex gap-3 sm:gap-4 mt-2 text-sm overflow-x-auto pb-1 scrollbar-hide -mx-1 px-1">
          {[
            { href: "/", label: "🔥 전체" },
            { href: "/?source=coupang", label: "🛒 쿠팡" },
            { href: "/?source=naver", label: "🛍️ 네이버" },
            { href: "/?source=community", label: "👥 커뮤니티" },
            { href: "/?category=전자기기", label: "📱 전자기기" },
            { href: "/?category=패션", label: "👗 패션" },
            { href: "/?category=식품", label: "🍱 식품" },
            { href: "/?category=뷰티", label: "💄 뷰티" },
            { href: "/?category=홈리빙", label: "🏠 홈리빙" },
            { href: "/?category=스포츠", label: "⚽ 스포츠" },
            { href: "/?hot_only=true", label: "⚡ 핫딜만" },
          ].map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="whitespace-nowrap text-white/80 hover:text-white hover:underline transition-colors text-xs sm:text-sm"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
