export default function DealCardSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="bg-gray-200 aspect-square w-full mb-2 rounded" />
      <div className="space-y-2 px-0.5">
        <div className="h-3 bg-gray-200 rounded w-1/3" />
        <div className="h-4 bg-gray-200 rounded w-full" />
        <div className="h-4 bg-gray-200 rounded w-4/5" />
        <div className="h-5 bg-gray-200 rounded w-2/5 mt-2" />
      </div>
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
