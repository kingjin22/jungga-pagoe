export default function DealSkeleton() {
  return (
    <div className="deal-card bg-white rounded-2xl overflow-hidden shadow-sm border border-gray-100 animate-pulse">
      {/* 이미지 스켈레톤 */}
      <div className="h-48 bg-gray-200" />

      {/* 내용 스켈레톤 */}
      <div className="p-3 space-y-3">
        {/* 제목 */}
        <div className="space-y-1.5">
          <div className="h-3.5 bg-gray-200 rounded w-full" />
          <div className="h-3.5 bg-gray-200 rounded w-4/5" />
        </div>

        {/* 가격 */}
        <div className="flex items-end gap-2">
          <div className="h-6 bg-gray-200 rounded w-24" />
          <div className="h-4 bg-gray-100 rounded w-16" />
        </div>

        {/* 하단 정보 */}
        <div className="flex items-center justify-between">
          <div className="h-3.5 bg-gray-100 rounded w-20" />
          <div className="h-7 bg-gray-200 rounded-full w-16" />
        </div>

        {/* 구매 버튼 */}
        <div className="h-9 bg-gray-200 rounded-xl w-full" />
      </div>
    </div>
  );
}

export function DealSkeletonGrid({ count = 10 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
      {Array.from({ length: count }).map((_, i) => (
        <DealSkeleton key={i} />
      ))}
    </div>
  );
}
