import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // 썸네일 최대 폭 제한 — 기본 3840px 제거 → 비용·LCP 개선
    deviceSizes: [320, 420, 640, 750, 828, 1080, 1200],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    minimumCacheTTL: 86400, // 24시간 캐시
    remotePatterns: [
      { protocol: "https", hostname: "cdn2.ppomppu.co.kr" },
      { protocol: "https", hostname: "**.ppomppu.co.kr" },
      { protocol: "https", hostname: "**.gmarket.co.kr" },
      { protocol: "https", hostname: "**.auction.co.kr" },
      { protocol: "https", hostname: "**.11st.co.kr" },
      { protocol: "https", hostname: "**.coupangcdn.com" },
      { protocol: "https", hostname: "thumbnail8.coupangcdn.com" },
      { protocol: "https", hostname: "**.naver.com" },
      { protocol: "https", hostname: "**.naver.net" },
      { protocol: "https", hostname: "**.lotteon.com" },
      { protocol: "https", hostname: "**.ssg.com" },
      { protocol: "https", hostname: "**.amazon.com" },
      { protocol: "https", hostname: "m.media-amazon.com" },
      { protocol: "https", hostname: "**.ebayimg.com" },
      { protocol: "https", hostname: "**.kakaocdn.net" },
      { protocol: "https", hostname: "**.kurly.com" },
      { protocol: "https", hostname: "**.oliveyoung.co.kr" },
      { protocol: "https", hostname: "**.musinsa.com" },
      // 와일드카드 fallback
      { protocol: "https", hostname: "**" },
    ],
  },
};

export default nextConfig;
