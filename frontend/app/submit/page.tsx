"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { submitDeal } from "@/lib/api";
import Link from "next/link";

const CATEGORIES = [
  { value: "전자기기", label: "전자기기" },
  { value: "패션", label: "패션" },
  { value: "식품", label: "식품" },
  { value: "뷰티", label: "뷰티" },
  { value: "홈리빙", label: "홈리빙" },
  { value: "스포츠", label: "스포츠" },
  { value: "유아동", label: "유아동" },
  { value: "기타", label: "기타" },
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
      ? Math.max(
          0,
          Math.round((1 - Number(form.sale_price) / Number(form.original_price)) * 100)
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
    } catch (err: any) {
      setError(err.message || "제보 중 오류가 발생했습니다");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="max-w-screen-xl mx-auto px-4 py-20 text-center">
        <div className="inline-block border border-gray-200 px-12 py-10">
          <p className="text-4xl font-black text-gray-900 mb-2">감사합니다</p>
          <p className="text-sm text-gray-500 mb-6">딜이 성공적으로 등록되었습니다.</p>
          <div className="flex gap-3 justify-center">
            <Link
              href="/"
              className="text-sm font-semibold bg-[#111] text-white px-6 py-2.5 hover:bg-[#333] transition-colors"
            >
              홈으로
            </Link>
            <button
              onClick={() => {
                setSuccess(false);
                setForm({
                  title: "", original_price: "", sale_price: "",
                  product_url: "", image_url: "", category: "기타",
                  description: "", submitter_name: "",
                });
              }}
              className="text-sm font-semibold border border-gray-200 px-6 py-2.5 text-gray-600 hover:border-gray-900 hover:text-gray-900 transition-colors"
            >
              추가 제보
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-10">
      {/* 페이지 헤더 */}
      <div className="mb-8 pb-6 border-b border-gray-200">
        <h1 className="text-2xl font-black text-gray-900 mb-1">딜 제보</h1>
        <p className="text-sm text-gray-500">
          발견한 핫딜을 공유해주세요. 추천 10개 이상이면 HOT 딜로 등록됩니다.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 제목 */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
            딜 제목 <span className="text-[#E31E24]">*</span>
          </label>
          <input
            type="text"
            required
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="예) 쿠팡 갤럭시 버즈3 프로 179,000원"
            className="w-full border border-gray-200 px-4 py-3 text-sm focus:border-gray-900 transition-colors"
          />
        </div>

        {/* 가격 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
              원래 가격 <span className="text-[#E31E24]">*</span>
            </label>
            <input
              type="number"
              required
              value={form.original_price}
              onChange={(e) => setForm({ ...form, original_price: e.target.value })}
              placeholder="299000"
              className="w-full border border-gray-200 px-4 py-3 text-sm focus:border-gray-900 transition-colors"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
              판매 가격 <span className="text-[#E31E24]">*</span>
            </label>
            <input
              type="number"
              required
              value={form.sale_price}
              onChange={(e) => setForm({ ...form, sale_price: e.target.value })}
              placeholder="179000"
              className="w-full border border-gray-200 px-4 py-3 text-sm focus:border-gray-900 transition-colors"
            />
          </div>
        </div>

        {/* 할인율 미리보기 */}
        {discountRate > 0 && (
          <div className="flex items-center gap-3 bg-gray-50 px-4 py-3 border border-gray-200">
            <span className="text-xs text-gray-500">예상 할인율</span>
            <span className={`text-xl font-black ${discountRate >= 30 ? "text-[#E31E24]" : "text-gray-700"}`}>
              -{discountRate}%
            </span>
            {discountRate < 10 && (
              <span className="text-xs text-orange-500">10% 이상인 딜만 등록 가능합니다</span>
            )}
          </div>
        )}

        {/* URL */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
            상품 링크 <span className="text-[#E31E24]">*</span>
          </label>
          <input
            type="url"
            required
            value={form.product_url}
            onChange={(e) => setForm({ ...form, product_url: e.target.value })}
            placeholder="https://www.coupang.com/..."
            className="w-full border border-gray-200 px-4 py-3 text-sm focus:border-gray-900 transition-colors"
          />
          {form.product_url.includes("coupang.com") && (
            <p className="text-[11px] text-blue-600 mt-1">
              ✓ 쿠팡 링크는 파트너스 링크로 자동 변환됩니다
            </p>
          )}
        </div>

        {/* 이미지 URL */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
            이미지 URL
            <span className="text-gray-400 font-normal ml-1">(선택)</span>
          </label>
          <input
            type="url"
            value={form.image_url}
            onChange={(e) => setForm({ ...form, image_url: e.target.value })}
            placeholder="https://..."
            className="w-full border border-gray-200 px-4 py-3 text-sm focus:border-gray-900 transition-colors"
          />
        </div>

        {/* 카테고리 */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
            카테고리
          </label>
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="w-full border border-gray-200 px-4 py-3 text-sm bg-white focus:border-gray-900 transition-colors"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        {/* 설명 */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
            추가 설명
            <span className="text-gray-400 font-normal ml-1">(선택)</span>
          </label>
          <textarea
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
            placeholder="만료일, 쿠폰 조건 등 추가 정보를 입력하세요"
            rows={3}
            className="w-full border border-gray-200 px-4 py-3 text-sm resize-none focus:border-gray-900 transition-colors"
          />
        </div>

        {/* 닉네임 */}
        <div>
          <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-2">
            닉네임
            <span className="text-gray-400 font-normal ml-1">(선택, 미입력시 익명)</span>
          </label>
          <input
            type="text"
            value={form.submitter_name}
            onChange={(e) => setForm({ ...form, submitter_name: e.target.value })}
            placeholder="익명"
            maxLength={20}
            className="w-full border border-gray-200 px-4 py-3 text-sm focus:border-gray-900 transition-colors"
          />
        </div>

        {error && (
          <div className="border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading || discountRate < 10}
          className="w-full bg-[#111] text-white font-bold py-4 text-sm hover:bg-[#333] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? "등록 중..." : "딜 제보하기"}
        </button>
      </form>
    </div>
  );
}
