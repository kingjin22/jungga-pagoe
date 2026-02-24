export default function DealCardSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="aspect-square bg-gray-200 rounded mb-2" />
      <div className="h-3 bg-gray-200 rounded mb-1" />
      <div className="h-3 bg-gray-200 rounded w-3/4 mb-2" />
      <div className="h-4 bg-gray-200 rounded w-1/2" />
    </div>
  );
}

export function DealGridSkeleton({ count = 10 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-x-4 gap-y-8">
      {Array.from({ length: count }).map((_, i) => <DealCardSkeleton key={i} />)}
    </div>
  );
}
