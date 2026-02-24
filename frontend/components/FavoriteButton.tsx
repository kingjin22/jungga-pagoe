"use client";
import { useFavorites } from "@/hooks/useFavorites";

export default function FavoriteButton({ dealId }: { dealId: number }) {
  const { toggle, isFav } = useFavorites();
  const fav = isFav(dealId);

  return (
    <button
      onClick={e => { e.preventDefault(); e.stopPropagation(); toggle(dealId); }}
      className={`absolute top-2 right-2 z-10 w-7 h-7 flex items-center justify-center rounded-full transition-all
        ${fav ? "bg-[#E31E24] text-white" : "bg-white/80 text-gray-400 hover:text-[#E31E24]"}`}
      aria-label={fav ? "찜 해제" : "찜하기"}
      title={fav ? "찜 해제" : "찜하기"}
    >
      <svg width="14" height="14" viewBox="0 0 24 24"
        fill={fav ? "currentColor" : "none"}
        stroke="currentColor" strokeWidth="2">
        <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>
      </svg>
    </button>
  );
}
