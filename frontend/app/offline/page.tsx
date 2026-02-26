"use client";

import { useEffect, useState } from "react";

export default function OfflinePage() {
  const [reconnecting, setReconnecting] = useState(false);

  // 인터넷 연결 복구 시 자동으로 홈으로 이동
  useEffect(() => {
    const handleOnline = () => {
      setReconnecting(true);
      // 잠깐 "연결됨" 상태 보여주고 홈으로 이동
      setTimeout(() => {
        window.location.href = "/";
      }, 800);
    };
    window.addEventListener("online", handleOnline);
    return () => window.removeEventListener("online", handleOnline);
  }, []);

  const handleRetry = () => {
    if (navigator.onLine) {
      window.location.href = "/";
    } else {
      // 오프라인 상태면 페이지 새로고침 시도
      window.location.reload();
    }
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center px-6">
      {reconnecting ? (
        <>
          {/* 재연결 성공 상태 */}
          <div className="w-20 h-20 rounded-full bg-emerald-50 flex items-center justify-center mb-6 animate-pulse">
            <svg
              width="40"
              height="40"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#059669"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <p className="text-lg font-bold text-emerald-600">연결됐어요!</p>
          <p className="text-sm text-gray-400 mt-1">잠시 후 이동합니다...</p>
        </>
      ) : (
        <>
          {/* 오프라인 아이콘 — 와이파이에 X 표시 */}
          <div className="relative w-24 h-24 mb-8" aria-hidden="true">
            {/* 와이파이 아이콘 SVG */}
            <svg
              width="96"
              height="96"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#D1D5DB"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 12.55a11 11 0 0 1 14.08 0" />
              <path d="M1.42 9a16 16 0 0 1 21.16 0" />
              <path d="M8.53 16.11a6 6 0 0 1 6.95 0" />
              <circle cx="12" cy="20" r="1" fill="#D1D5DB" stroke="none" />
            </svg>
            {/* X 배지 */}
            <div className="absolute -top-1 -right-1 w-7 h-7 bg-red-500 rounded-full flex items-center justify-center">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="white"
                strokeWidth="3"
                strokeLinecap="round"
              >
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </div>
          </div>

          <h1 className="text-xl font-bold text-gray-900 mb-2">인터넷에 연결되지 않았어요</h1>
          <p className="text-sm text-gray-400 mb-1">와이파이 또는 데이터 연결을 확인해주세요.</p>
          <p className="text-xs text-gray-300 mb-10">연결이 복구되면 자동으로 핫딜 페이지로 이동합니다</p>

          <button
            onClick={handleRetry}
            className="flex items-center gap-2 bg-gray-900 text-white text-sm font-semibold px-6 py-3 hover:bg-gray-700 transition-colors active:scale-95 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900"
            aria-label="다시 시도"
          >
            <svg
              width="15"
              height="15"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="23 4 23 10 17 10" />
              <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
            </svg>
            다시 시도
          </button>

          {/* 연결 대기 중 인디케이터 */}
          <div className="mt-10 flex items-center gap-1.5" aria-live="polite" aria-label="연결 대기 중">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-gray-200 animate-bounce"
                style={{ animationDelay: `${i * 0.15}s` }}
                aria-hidden="true"
              />
            ))}
            <span className="text-xs text-gray-300 ml-1">연결 대기 중</span>
          </div>
        </>
      )}
    </div>
  );
}
