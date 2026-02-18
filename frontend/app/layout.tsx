import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Header from "@/components/Header";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

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
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen`}
      >
        <Header />
        <main className="max-w-7xl mx-auto px-4 py-6">
          {children}
        </main>
        <footer className="text-center text-xs text-gray-400 py-8 mt-4 border-t">
          <p>정가파괴 © 2025 · 이 사이트의 일부 링크는 제휴 마케팅 링크입니다</p>
          <p className="mt-1">쿠팡 파트너스 활동을 통해 일정액의 수수료를 제공받을 수 있습니다</p>
        </footer>
      </body>
    </html>
  );
}
