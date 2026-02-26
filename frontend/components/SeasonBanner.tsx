"use client";

import { useRouter } from "next/navigation";

// C-013: 시즌 특화 큐레이션 배너 (쿠차 스타일)
const currentSeason = {
  name: "봄/신학기",
  emoji: "🌸",
  keywords: ["운동화", "가방", "학용품", "바람막이", "패션", "봄"],
};

const filterTags = [
  { emoji: "🌸", label: "봄", keyword: "봄" },
  { emoji: "👟", label: "운동화", keyword: "운동화" },
  { emoji: "🎒", label: "가방", keyword: "가방" },
  { emoji: "📚", label: "학용품", keyword: "학용품" },
  { emoji: "🧥", label: "바람막이", keyword: "바람막이" },
];

export default function SeasonBanner() {
  const router = useRouter();

  const handleBannerClick = () => {
    router.push(`/search?q=${encodeURIComponent("봄")}`);
  };

  const handleTagClick = (keyword: string) => {
    router.push(`/search?q=${encodeURIComponent(keyword)}`);
  };

  return (
    <div className="mb-5">
      {/* 메인 배너 */}
      <button
        onClick={handleBannerClick}
        className="w-full text-left rounded-xl overflow-hidden relative cursor-pointer group"
        style={{
          background: "linear-gradient(135deg, #fce4ec 0%, #f8bbd0 40%, #dcedc8 100%)",
        }}
        aria-label={`${currentSeason.name} 시즌 특가 딜 보기`}
      >
        <div className="px-4 py-4 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <span className="text-[10px] font-bold text-pink-500 tracking-widest uppercase">
                SEASON DEAL
              </span>
            </div>
            <h3 className="text-base font-black text-gray-800 leading-tight">
              {currentSeason.emoji} {currentSeason.name} 특가 모음
            </h3>
            <p className="text-[12px] text-gray-500 mt-0.5">
              새 학기 준비, 지금이 찬스 🎯
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className="text-2xl">{currentSeason.emoji}</span>
            <span className="text-[11px] font-semibold text-pink-500 group-hover:underline">
              딜 보기 →
            </span>
          </div>
        </div>
      </button>

      {/* 빠른 필터 태그 */}
      <div className="flex flex-wrap gap-2 mt-2.5">
        {filterTags.map((tag) => (
          <button
            key={tag.keyword}
            onClick={() => handleTagClick(tag.keyword)}
            className="flex items-center gap-1 text-[12px] font-semibold px-3 py-1.5 rounded-full border transition-all
              bg-white border-pink-200 text-gray-700 hover:bg-pink-50 hover:border-pink-400 hover:text-pink-700 active:scale-95"
          >
            <span>{tag.emoji}</span>
            <span>{tag.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
