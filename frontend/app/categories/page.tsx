import Link from "next/link";
import { CATEGORIES } from "@/lib/categories";

export const metadata = { title: "카테고리 | 정가파괴" };

export default function CategoriesPage() {
  const cats = Object.values(CATEGORIES);

  return (
    <div className="max-w-screen-xl mx-auto px-4 py-8">
      <h1 className="text-xl font-bold mb-6">카테고리</h1>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
        {cats.map(cat => (
          <Link key={cat.slug} href={`/category/${cat.slug}`}
            className="border border-gray-200 rounded-lg p-4 hover:border-gray-400 transition-colors">
            <div className="text-2xl mb-2">{cat.emoji || "🏷️"}</div>
            <div className="font-semibold text-sm">{cat.name}</div>
            <div className="text-xs text-gray-400 mt-1 line-clamp-2">{cat.desc}</div>
          </Link>
        ))}
      </div>
    </div>
  );
}
