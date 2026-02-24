"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useFavorites } from "@/hooks/useFavorites";

const tabs = [
  { href: "/", label: "홈", icon: (active: boolean) => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? "currentColor" : "none"}
      stroke="currentColor" strokeWidth="1.8">
      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
      <polyline points="9 22 9 12 15 12 15 22"/>
    </svg>
  )},
  { href: "/categories", label: "카테고리", icon: (_active: boolean) => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8">
      <rect x="3" y="3" width="7" height="7" rx="1"/>
      <rect x="14" y="3" width="7" height="7" rx="1"/>
      <rect x="3" y="14" width="7" height="7" rx="1"/>
      <rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>
  )},
  { href: "/?focus=search", label: "검색", icon: (_active: boolean) => (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="1.8">
      <circle cx="11" cy="11" r="8"/>
      <line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
  )},
  { href: "/favorites", label: "찜", icon: (active: boolean) => (
    <svg width="22" height="22" viewBox="0 0 24 24"
      fill={active ? "currentColor" : "none"}
      stroke="currentColor" strokeWidth="1.8">
      <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
    </svg>
  )},
];

export default function BottomNav() {
  const pathname = usePathname();
  const { count } = useFavorites();

  if (pathname.startsWith("/admin")) return null;

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-gray-200 md:hidden">
      <div className="grid grid-cols-4 h-14">
        {tabs.map(tab => {
          const isActive = tab.href === "/" ? pathname === "/" : pathname.startsWith(tab.href.split("?")[0]);
          return (
            <Link key={tab.href} href={tab.href}
              className={`flex flex-col items-center justify-center gap-0.5 text-[10px] font-medium transition-colors
                ${isActive ? "text-[#E31E24]" : "text-gray-400"}`}>
              <div className="relative">
                {tab.icon(isActive)}
                {tab.label === "찜" && count > 0 && (
                  <span className="absolute -top-1 -right-1 bg-[#E31E24] text-white text-[8px] rounded-full w-3.5 h-3.5 flex items-center justify-center leading-none">
                    {count > 9 ? "9+" : count}
                  </span>
                )}
              </div>
              <span>{tab.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
