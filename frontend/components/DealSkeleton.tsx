export default function DealSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="aspect-square bg-gray-200 mb-2" />
      <div className="h-2 bg-gray-200 w-16 mb-1.5" />
      <div className="h-3 bg-gray-200 w-full mb-1" />
      <div className="h-3 bg-gray-200 w-3/4 mb-2" />
      <div className="h-4 bg-gray-200 w-24 mb-1" />
      <div className="h-3 bg-gray-200 w-16" />
    </div>
  );
}

export function DealGridSkeleton({ count = 10 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-x-4 gap-y-8">
      {Array.from({ length: count }).map((_, i) => (
        <DealSkeleton key={i} />
      ))}
    </div>
  );
}
