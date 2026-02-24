import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
      <p className="text-6xl font-black text-gray-100 mb-4">404</p>
      <h1 className="text-xl font-bold mb-2">페이지를 찾을 수 없어요</h1>
      <p className="text-sm text-gray-400 mb-8">이미 만료된 딜이거나 잘못된 주소예요</p>
      <div className="flex gap-3">
        <Link
          href="/"
          className="px-6 py-2.5 bg-[#E31E24] text-white text-sm font-medium hover:bg-[#c41920] transition-colors"
        >
          핫딜 보러가기
        </Link>
        <Link
          href="/favorites"
          className="px-6 py-2.5 border border-gray-300 text-sm font-medium hover:border-gray-500 transition-colors"
        >
          내 찜 목록
        </Link>
      </div>
    </div>
  );
}
