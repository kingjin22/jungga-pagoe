"use client";

import { useEffect, useState } from "react";

/**
 * ScrollToTop — 스크롤 내려갔을 때 상단으로 돌아가는 플로팅 버튼
 *
 * 개선 포인트:
 * - 400px 이상 스크롤 시 자연스럽게 페이드인
 * - 클릭 시 부드러운 스무스 스크롤
 * - 모바일 BottomNav 위에 위치 (bottom-20 md:bottom-8)
 * - aria-label로 스크린리더 접근성 확보
 * - 애니메이션: opacity + translateY 조합으로 자연스러운 등장
 */
export default function ScrollToTop() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => {
      setVisible(window.scrollY > 400);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <button
      onClick={scrollToTop}
      aria-label="맨 위로 이동"
      className={`
        fixed right-4 bottom-20 md:bottom-8 z-40
        w-10 h-10 rounded-full shadow-lg
        bg-white border border-gray-200
        flex items-center justify-center
        text-gray-600 hover:text-gray-900
        hover:shadow-xl hover:border-gray-400
        transition-all duration-300
        active:scale-90
        ${visible
          ? "opacity-100 translate-y-0 pointer-events-auto"
          : "opacity-0 translate-y-2 pointer-events-none"
        }
      `}
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <polyline points="18 15 12 9 6 15" />
      </svg>
    </button>
  );
}
