"use client";
import { useState } from "react";

interface Props {
  title: string;
  salePrice: number;
  discountRate: number;
  imageUrl?: string;
  dealUrl: string;
}

const kakaoKey = process.env.NEXT_PUBLIC_KAKAO_JS_KEY;

export default function ShareButtons({ title, salePrice, discountRate, imageUrl, dealUrl }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopyLink = async () => {
    await navigator.clipboard.writeText(dealUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleTwitterShare = () => {
    const text = `${title} — ${Math.round(discountRate)}% 할인 ${salePrice.toLocaleString()}원 | 정가파괴`;
    window.open(
      `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(dealUrl)}`,
      "_blank"
    );
  };

  const handleKakaoShare = () => {
    const kakao = (window as any).Kakao;
    if (!kakao?.isInitialized()) return;
    kakao.Share.sendDefault({
      objectType: "commerce",
      content: {
        title: title.slice(0, 60),
        imageUrl: imageUrl || "https://jungga-pagoe.vercel.app/og-default.png",
        link: { mobileWebUrl: dealUrl, webUrl: dealUrl },
      },
      commerce: {
        productName: title.slice(0, 30),
        regularPrice: Math.round(salePrice / (1 - discountRate / 100)),
        salePrice: salePrice,
        discountRate: Math.round(discountRate),
      },
      buttons: [{ title: "딜 보러가기", link: { mobileWebUrl: dealUrl, webUrl: dealUrl } }],
    });
  };

  return (
    <div className="flex items-center gap-2">
      {kakaoKey && (
        <button
          onClick={handleKakaoShare}
          className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium bg-[#FEE500] text-[#391B1B] rounded hover:opacity-90 transition-opacity"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 3C6.477 3 2 6.477 2 10.8c0 2.7 1.6 5.1 4 6.6L5 21l4.3-2.4c.87.16 1.78.24 2.7.24 5.523 0 10-3.477 10-7.8S17.523 3 12 3z" />
          </svg>
          카카오 공유
        </button>
      )}
      <button
        onClick={handleTwitterShare}
        className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium border border-gray-300 text-gray-600 rounded hover:border-gray-500 transition-colors"
      >
        X(트위터)
      </button>
      <button
        onClick={handleCopyLink}
        className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium border border-gray-300 text-gray-600 rounded hover:border-gray-500 transition-colors"
      >
        {copied ? "복사됨 ✓" : "링크 복사"}
      </button>
    </div>
  );
}
