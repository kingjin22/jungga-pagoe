import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "정가파괴 - 쿠팡/네이버 핫딜 모음",
  description: "쿠팡, 네이버 핫딜을 자동 수집하고 커뮤니티가 제보하는 진짜 할인 정보",
  keywords: ["핫딜", "쿠팡", "네이버", "할인", "특가", "세일"],
  openGraph: {
    title: "정가파괴",
    description: "진짜 핫딜만 모인 곳",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-white">
        <Header />
        <main>{children}</main>
        <footer className="border-t border-gray-200 mt-16">
          <div className="max-w-screen-xl mx-auto px-4 py-10">
            <div className="flex flex-col md:flex-row justify-between gap-6">
              <div>
                <p className="font-black text-lg tracking-tight mb-1">정가파괴</p>
                <p className="text-xs text-gray-400 leading-relaxed">
                  본 사이트의 일부 링크는 제휴 마케팅 링크입니다.<br />
                  쿠팡 파트너스 활동을 통해 일정액의 수수료를 제공받을 수 있습니다.
                </p>
              </div>
              <div className="flex gap-8 text-xs text-gray-400">
                <div>
                  <p className="font-semibold text-gray-600 mb-2">서비스</p>
                  <ul className="space-y-1">
                    <li><a href="/submit" className="hover:text-gray-900">딜 제보</a></li>
                  </ul>
                </div>
              </div>
            </div>
            <div className="mt-8 pt-6 border-t border-gray-100 text-xs text-gray-300">
              © 2025 정가파괴. All rights reserved.
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
