"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { submitDeal } from "@/lib/api";

const CATEGORIES = [
  { value: "전자기기", label: "📱 전자기기" },
  { value: "패션", label: "👗 패션" },
  { value: "식품", label: "🍱 식품" },
  { value: "뷰티", label: "💄 뷰티" },
  { value: "홈리빙", label: "🏠 홈리빙" },
  { value: "스포츠", label: "⚽ 스포츠" },
  { value: "유아동", label: "🧒 유아동" },
  { value: "기타", label: "📦 기타" },
];

export default function SubmitPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    title: "",
    original_price: "",
    sale_price: "",
    product_url: "",
    image_url: "",
    category: "기타",
    description: "",
    submitter_name: "",
  });

  const discountRate =
    form.original_price && form.sale_price
      ? Math.round(
          (1 - Number(form.sale_price) / Number(form.original_price)) * 100
        )
      : 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      await submitDeal({
        ...form,
        original_price: Number(form.original_price),
        sale_price: Number(form.sale_price),
      });
      setSuccess(true);
      setTimeout(() => router.push("/"), 2000);
    } catch (err: any) {
      setError(err.message || "제보 중 오류가 발생했습니다");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="max-w-lg mx-auto text-center py-20">
        <div className="text-6xl mb-4">🎉</div>
        <h2 className="text-2xl font-black text-[#E31E24] mb-2">제보 완료!</h2>
        <p className="text-gray-600">딜이 등록되었습니다. 메인으로 이동합니다...</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-black text-gray-900">💡 딜 제보하기</h1>
        <p className="text-gray-500 mt-1">
          핫딜을 발견했나요? 커뮤니티에 공유하세요! 추천 10개 이상이면 🔥 HOT 배지!
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-4"
      >
        {/* 제목 */}
        <div>
          <label className="block text-sm font-bold text-gray-700 mb-1">
            딜 제목 <span className="text-[#E31E24]">*</span>
          </label>
          <input
            type="text"
            required
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="예: [쿠팡] 갤럭시 버즈3 프로 179,000원"
            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-[#E31E24] transition-colors"
          />
        </div>

        {/* 가격 */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-1">
              원래 가격 <span className="text-[#E31E24]">*</span>
            </label>
            <input
              type="number"
              required
              value={form.original_price}
              onChange={(e) => setForm({ ...form, original_price: e.target.value })}
              placeholder="299000"
              className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-[#E31E24] transition-colors"
            />
          </div>
          <div>
            <label className="block text-sm font-bold text-gray-700 mb-1">
              판매 가격 <span className="text-[#E31E24]">*</span>
            </label>
            <input
              type="number"
              required
              value={form.sale_price}
              onChange={(e) => setForm({ ...form, sale_price: e.target.value })}
              placeholder="179000"
              className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-[#E31E24] transition-colors"
            />
          </div>
        </div>

        {/* 할인율 미리보기 */}
        {discountRate > 0 && (
          <div
            className={`text-center py-2 rounded-xl font-black text-lg ${
              discountRate >= 40
                ? "bg-red-50 text-[#E31E24]"
                : discountRate >= 20
                ? "bg-orange-50 text-orange-600"
                : "bg-yellow-50 text-yellow-600"
            }`}
          >
            할인율: -{discountRate}%{" "}
            {discountRate >= 50 ? "🔥🔥🔥" : discountRate >= 30 ? "🔥" : ""}
          </div>
        )}

        {/* 상품 URL */}
        <div>
          <label className="block text-sm font-bold text-gray-700 mb-1">
            상품 링크 <span className="text-[#E31E24]">*</span>
          </label>
          <input
            type="url"
            required
            value={form.product_url}
            onChange={(e) => setForm({ ...form, product_url: e.target.value })}
            placeholder="https://www.coupang.com/..."
            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-[#E31E24] transition-colors"
          />
          {form.product_url.includes("coupang.com") && (
            <p className="text-xs text-orange-600 mt-1">
              ✓ 쿠팡 링크는 자동으로 파트너스 링크로 변환됩니다
            </p>
          )}
        </div>

        {/* 이미지 URL */}
        <div>
          <label className="block text-sm font-bold text-gray-700 mb-1">
            이미지 URL (선택)
          </label>
          <input
            type="url"
            value={form.image_url}
            onChange={(e) => setForm({ ...form, image_url: e.target.value })}
            placeholder="https://..."
            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-[#E31E24] transition-colors"
          />
        </div>

        {/* 카테고리 */}
        <div>
          <label className="block text-sm font-bold text-gray-700 mb-1">카테고리</label>
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-[#E31E24] transition-colors bg-white"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>
                {c.label}
              </option>
            ))}
          </select>
        </div>

        {/* 설명 */}
        <div>
          <label className="block text-sm font-bold text-gray-700 mb-1">
            추가 설명 (선택)
          </label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="딜에 대한 추가 정보를 알려주세요 (만료일, 조건 등)"
            rows={3}
            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-[#E31E24] transition-colors resize-none"
          />
        </div>

        {/* 닉네임 */}
        <div>
          <label className="block text-sm font-bold text-gray-700 mb-1">
            닉네임 (선택)
          </label>
          <input
            type="text"
            value={form.submitter_name}
            onChange={(e) => setForm({ ...form, submitter_name: e.target.value })}
            placeholder="익명"
            maxLength={20}
            className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none focus:border-[#E31E24] transition-colors"
          />
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl px-4 py-3 text-sm">
            ⚠️ {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-[#E31E24] text-white font-black py-3 rounded-xl text-base hover:bg-[#B71C1C] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "제보 중..." : "🔥 딜 제보하기"}
        </button>
      </form>
    </div>
  );
}
