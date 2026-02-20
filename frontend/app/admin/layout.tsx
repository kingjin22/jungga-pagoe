"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { isAdminLoggedIn, adminLogout } from "@/lib/admin-api";

export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [mounted, setMounted] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);  // 훅은 항상 최상단에

  useEffect(() => {
    setMounted(true);
    if (pathname !== "/admin/login" && !isAdminLoggedIn()) {
      router.replace("/admin/login");
    }
  }, [pathname, router]);

  useEffect(() => {
    if (pathname === "/admin/login") return;
    if (!isAdminLoggedIn()) return;
    import("@/lib/admin-api").then(({ getPendingDeals }) => {
      getPendingDeals().then((r: { total: number }) => setPendingCount(r.total ?? 0)).catch(() => {});
    });
  }, [pathname]);

  // 로그인 페이지는 레이아웃 없이 렌더
  if (pathname === "/admin/login") {
    return <>{children}</>;
  }

  if (!mounted) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <span className="text-gray-400 text-sm">Loading...</span>
      </div>
    );
  }

  if (!isAdminLoggedIn()) {
    return null;
  }

  const navItems = [
    { href: "/admin/dashboard", label: "대시보드" },
    { href: "/admin/add-deal", label: "➕ 딜 빠른 등록" },
    { href: "/admin/deals", label: "딜 관리" },
    { href: "/admin/review", label: "제보 검토", badge: pendingCount },
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <aside className="w-52 shrink-0 bg-white border-r border-gray-200 flex flex-col">
        <div className="px-5 py-4 border-b border-gray-200">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-wider">
            정가파괴
          </p>
          <p className="text-base font-bold text-gray-900 mt-0.5">Admin</p>
        </div>
        <nav className="flex-1 py-3">
          {navItems.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center justify-between px-5 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "text-[#E31E24] bg-red-50 border-r-2 border-[#E31E24]"
                    : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                }`}
              >
                {item.label}
                {"badge" in item && (item as {badge?: number}).badge! > 0 && (
                  <span className="bg-[#E31E24] text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full min-w-[18px] text-center">
                    {(item as {badge?: number}).badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-gray-200">
          <button
            onClick={adminLogout}
            className="w-full text-left text-xs text-gray-400 hover:text-gray-700 transition-colors"
          >
            로그아웃
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  );
}
