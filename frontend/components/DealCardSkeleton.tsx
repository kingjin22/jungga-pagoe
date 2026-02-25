/**
 * DealCardSkeleton — 실제 DealCard 레이아웃과 구조를 맞춘 스켈레톤
 *
 * 개선 포인트:
 *  - shimmer(shine) 애니메이션으로 로딩 느낌 자연스럽게
 *  - 실제 카드와 동일한 레이아웃 계층 유지 (이미지, 제목 2줄, 가격, 버튼)
 *  - 배지 위치도 반영해 시각적 점프 최소화
 */
function Shimmer({ className }: { className?: string }) {
  return (
    <div
      className={`relative overflow-hidden bg-gray-100 rounded ${className ?? ""}`}
    >
      <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.4s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-white/60 to-transparent" />
    </div>
  );
}

export default function DealCardSkeleton() {
  return (
    <div aria-hidden="true">
      {/* 이미지 영역 */}
      <div className="relative w-full aspect-square bg-gray-100 overflow-hidden rounded-none">
        {/* 좌상단 배지 자리 */}
        <Shimmer className="absolute top-0 left-0 w-12 h-5 rounded-none" />
        {/* 좌하단 출처 칩 자리 */}
        <Shimmer className="absolute bottom-2 left-2 w-10 h-4 rounded-none" />
        {/* 전체 이미지 shimmer */}
        <div className="absolute inset-0 -translate-x-full animate-[shimmer_1.4s_ease-in-out_infinite] bg-gradient-to-r from-transparent via-white/50 to-transparent" />
      </div>

      {/* 텍스트 영역 */}
      <div className="pt-2 pb-3 space-y-2">
        {/* 카테고리 + 시간 행 */}
        <div className="flex justify-between">
          <Shimmer className="h-3 w-16" />
          <Shimmer className="h-3 w-10" />
        </div>

        {/* 제목 2줄 */}
        <Shimmer className="h-3.5 w-full" />
        <Shimmer className="h-3.5 w-4/5" />

        {/* 가격 행 */}
        <div className="flex items-baseline gap-2 pt-0.5">
          <Shimmer className="h-5 w-10" />
          <Shimmer className="h-5 w-20" />
        </div>

        {/* 정가 */}
        <Shimmer className="h-3 w-16" />

        {/* 구분선 + 하단 메타 */}
        <div className="flex justify-between pt-1 border-t border-gray-100">
          <Shimmer className="h-3 w-14" />
          <Shimmer className="h-3 w-8" />
        </div>

        {/* 구매 버튼 */}
        <Shimmer className="h-9 w-full mt-1" />
      </div>
    </div>
  );
}

export function DealGridSkeleton({ count = 10 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-x-4 gap-y-8">
      {Array.from({ length: count }).map((_, i) => (
        <DealCardSkeleton key={i} />
      ))}
    </div>
  );
}
