import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import Header from "@/components/Header";
import { getCategories } from "@/lib/api";

export const metadata: Metadata = {
  metadataBase: new URL("https://jungga-pagoe.vercel.app"),
  title: "정가파괴 - 핫딜 최저가 모음",
  description: "Apple, Samsung, Nike, Dyson 등 브랜드 공식 정가 대비 최저가를 실시간 추적. 뽐뿌·쿠팡·네이버 핫딜을 한곳에서 확인하세요.",
  keywords: ["핫딜", "최저가", "쿠팡 핫딜", "네이버 핫딜", "할인", "특가", "세일", "애플 할인", "나이키 최저가", "다이슨 할인"],
  openGraph: {
    title: "정가파괴 - 핫딜 최저가 모음",
    description: "브랜드 공식 정가 대비 진짜 할인만 모은 핫딜 플랫폼",
    type: "website",
    locale: "ko_KR",
  },
  alternates: {
    canonical: "https://jungga-pagoe.vercel.app",
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const categories = await getCategories().catch(() => []);
  const categoryNames = categories.map((c) => c.category);

  const orgJsonLd = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "정가파괴",
    url: "https://jungga-pagoe.vercel.app",
    description: "브랜드 공식 정가 대비 진짜 할인만 모은 핫딜 플랫폼",
    potentialAction: {
      "@type": "SearchAction",
      target: "https://jungga-pagoe.vercel.app/?search={search_term_string}",
      "query-input": "required name=search_term_string",
    },
  };

  return (
    <html lang="ko">
      <head>
        {/* Google AdSense - 정적 HTML에 삽입해 Google 크롤러 검증 통과 */}
        {/* eslint-disable-next-line @next/next/no-sync-scripts */}
        <script
          async
          src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=ca-pub-1679118656531907"
          crossOrigin="anonymous"
        />
      </head>
      <body className="min-h-screen bg-white">
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(orgJsonLd) }}
        />
        <Suspense fallback={<div className="h-14 bg-white border-b border-gray-200" />}>
          <Header categories={categoryNames} />
        </Suspense>
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
              © 2026 정가파괴. All rights reserved.
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
