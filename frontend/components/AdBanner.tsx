"use client";
import { useEffect, useRef } from "react";

interface AdBannerProps {
  slot: string;           // 광고 슬롯 ID
  format?: "auto" | "rectangle" | "horizontal";
  className?: string;
}

declare global {
  interface Window { adsbygoogle: unknown[] }
}

export default function AdBanner({ slot, format = "auto", className = "" }: AdBannerProps) {
  const adRef = useRef<HTMLModElement>(null);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch {}
  }, []);

  // 개발 환경에서는 placeholder 표시
  if (process.env.NODE_ENV === "development") {
    return (
      <div className={`flex items-center justify-center bg-gray-100 border border-dashed border-gray-300 text-gray-400 text-xs ${className}`}
        style={{ minHeight: 90 }}>
        📢 광고 영역 (슬롯: {slot})
      </div>
    );
  }

  return (
    <ins
      ref={adRef}
      className={`adsbygoogle ${className}`}
      style={{ display: "block" }}
      data-ad-client={process.env.NEXT_PUBLIC_ADSENSE_CLIENT_ID}
      data-ad-slot={slot}
      data-ad-format={format}
      data-full-width-responsive="true"
    />
  );
}
