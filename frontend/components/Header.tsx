"use client";

import Link from "next/link";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import SearchBar from "@/components/SearchBar";
import { useFavorites } from "@/hooks/useFavorites";

// 소스 필터는 고정 (출처 기반)
const SOURCE_LINKS = [
  { href: "/", label: "전체" },
  { href: "/?source=coupang", label: "쿠팡" },
  { href: "/?source=naver", label: "네이버" },
  { href: "/?source=community", label: "커뮤니티" },
  { href: "/?hot_only=true", label: "HOT딜", hot: true },
];

interface HeaderProps {
  categories?: string[]; // 서버에서 내려주는 동적 카테고리 목록
}

export default function Header({ categories = [] }: HeaderProps) {
  const [searchOpen, setSearchOpen] = useState(false);
  const searchParams = useSearchParams();
  const { count: favCount } = useFavorites();

  const currentCategory = searchParams.get("category") || "";
  const currentSource = searchParams.get("source") || "";
  const isHotOnly = searchParams.get("hot_only") === "true";

  return (
    <header className="sticky top-0 z-50 bg-white border-b border-gray-200">
      {/* 최상단 바 */}
      <div className="bg-[#111] text-white">
        <div className="max-w-screen-xl mx-auto px-4 py-2 flex items-center justify-between">
          <Link href="/" className="flex items-baseline gap-2">
            <span className="font-black text-xl tracking-tight text-white">정가파괴</span>
            <span className="hidden sm:block text-[11px] text-gray-400 font-normal">실시간 핫딜 · 역대 최저가</span>
          </Link>

          <div className="flex items-center gap-4">
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

            <Link href="/favorites" className="relative text-gray-400 hover:text-white transition-colors" aria-label="찜한 딜">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
              </svg>
              {favCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-[#E31E24] text-white text-[9px] rounded-full w-4 h-4 flex items-center justify-center leading-none">
                  {favCount > 99 ? "99+" : favCount}
                </span>
              )}
            </Link>

            <Link
              href="/submit"
              className="text-xs font-semibold bg-[#E31E24] text-white px-3 py-1.5 hover:bg-[#c01920] transition-colors"
            >
              딜 제보
            </Link>
          </div>
        </div>

        {searchOpen && (
          <div className="border-t border-gray-700">
            <div className="max-w-screen-xl mx-auto px-4 py-3 flex gap-2">
              <SearchBar onClose={() => setSearchOpen(false)} />
            </div>
          </div>
        )}
      </div>

      {/* 네비 — 소스 + 동적 카테고리 */}
      <div className="bg-white">
        <div className="max-w-screen-xl mx-auto px-4">
          <nav className="flex overflow-x-auto scrollbar-hide">
            {/* 고정 소스 필터 */}
            {SOURCE_LINKS.map((item) => {
              const isActive = item.hot
                ? isHotOnly
                : item.href === "/"
                ? !currentSource && !currentCategory && !isHotOnly
                : currentSource === item.href.replace("/?source=", "");

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`shrink-0 px-4 py-3 text-sm border-b-2 transition-colors whitespace-nowrap ${
                    item.hot
                      ? isActive
                        ? "text-[#E31E24] border-[#E31E24] font-black"
                        : "text-[#E31E24] border-transparent hover:border-[#E31E24] font-bold"
                      : isActive
                      ? "text-gray-900 border-gray-900 font-bold"
                      : "text-gray-500 border-transparent hover:text-gray-900 hover:border-gray-300 font-medium"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}

            {/* 구분선 */}
            {categories.length > 0 && (
              <span className="self-center mx-1 text-gray-200 text-lg select-none">|</span>
            )}

            {/* 동적 카테고리 */}
            {categories.map((cat) => {
              const isActive = currentCategory === cat;
              return (
                <Link
                  key={cat}
                  href={isActive ? "/" : `/?category=${encodeURIComponent(cat)}`}
                  className={`shrink-0 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                    isActive
                      ? "text-gray-900 border-gray-900 font-bold"
                      : "text-gray-500 border-transparent hover:text-gray-900 hover:border-gray-300"
                  }`}
                >
                  {cat}
                </Link>
              );
            })}

            {/* 구분선 + 특별 섹션 링크 */}
            <span className="self-center mx-1 text-gray-200 text-lg select-none">|</span>
            <Link href="/group-buy" className="shrink-0 px-4 py-3 text-sm text-gray-500 border-b-2 border-transparent whitespace-nowrap hover:text-gray-900">
              🛒 공구
            </Link>
            <Link href="/gifticon" className="shrink-0 px-4 py-3 text-sm text-gray-500 border-b-2 border-transparent whitespace-nowrap hover:text-gray-900">
              🎁 기프티콘
            </Link>
            <Link href="/raffle" className="shrink-0 px-4 py-3 text-sm text-gray-500 border-b-2 border-transparent whitespace-nowrap hover:text-gray-900">
              🎯 래플
            </Link>
            <Link href="/coupon" className="shrink-0 px-4 py-3 text-sm text-gray-500 border-b-2 border-transparent whitespace-nowrap hover:text-gray-900">
              🎫 쿠폰
            </Link>
            <Link href="/preorder" className="shrink-0 px-4 py-3 text-sm text-gray-500 border-b-2 border-transparent whitespace-nowrap hover:text-gray-900">
              🚀 사전구매
            </Link>
            <Link href="/timedeal" className="shrink-0 px-4 py-3 text-sm text-gray-500 border-b-2 border-transparent whitespace-nowrap hover:text-gray-900">
              ⚡ 타임딜
            </Link>
            <Link href="/fashion" className="shrink-0 px-4 py-3 text-sm text-gray-500 border-b-2 border-transparent whitespace-nowrap hover:text-gray-900">
              👟 패션·신발
            </Link>
            <Link href="/electronics" className="shrink-0 px-4 py-3 text-sm text-gray-500 border-b-2 border-transparent whitespace-nowrap hover:text-gray-900">
              💻 전자기기
            </Link>
          </nav>
        </div>
      </div>
    </header>
  );
}
