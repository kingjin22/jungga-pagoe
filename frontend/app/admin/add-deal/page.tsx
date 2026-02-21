"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const getAdminKey = () =>
  typeof window !== "undefined" ? localStorage.getItem("admin_key") || "" : "";

const CATEGORIES = [
  "신발", "전자기기", "생활가전", "패션", "뷰티", "스포츠", "유아동", "기타",
];

interface NaverResult {
  title: string;
  lprice: number;
  hprice: number;
  image: string;
  brand: string;
}

interface FormState {
  product_url: string;
  title: string;
  original_price: string;
  sale_price: string;
  category: string;
  image_url: string;
  description: string;
  source: string;
}

export default function AddDealPage() {
  const router = useRouter();

  // URL 자동 파싱
  const [parseLoading, setParseLoading] = useState(false);
  const [parseError, setParseError] = useState("");

  // Naver 자동완성
  const [lookupQuery, setLookupQuery] = useState("");
  const [lookupResults, setLookupResults] = useState<NaverResult[]>([]);
  const [lookupLoading, setLookupLoading] = useState(false);

  const [form, setForm] = useState<FormState>({
    product_url: "",
    title: "",
    original_price: "",
    sale_price: "",
    category: "",
    image_url: "",
    description: "",
    source: "admin",
  });

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState<{ id: number; title: string } | null>(null);

  const discountRate =
    form.original_price && form.sale_price
      ? Math.round((1 - Number(form.sale_price) / Number(form.original_price)) * 100)
      : null;

  const isCoupangPartners =
    form.product_url.toLowerCase().includes("link.coupang.com");
  const isCoupangDirect =
    (form.product_url.toLowerCase().includes("coupang.com") ||
      form.product_url.toLowerCase().includes("coupa.ng")) &&
    !isCoupangPartners;

  /* ── URL → 자동 파싱 ── */
  const handleParseUrl = async (url?: string) => {
    const targetUrl = url || form.product_url;
    if (!targetUrl.startsWith("http")) return;
    setParseLoading(true);
    setParseError("");
    try {
      const res = await fetch(
        `${API_BASE}/admin/parse-url?url=${encodeURIComponent(targetUrl)}`,
        { headers: { "X-Admin-Key": getAdminKey() } }
      );
      const data = await res.json();
      if (data.error) {
        setParseError(data.error);
        return;
      }
      setForm((f) => ({
        ...f,
        product_url: url || f.product_url,
        title: data.title || f.title,
        sale_price: data.sale_price ? String(data.sale_price) : f.sale_price,
        original_price: data.original_price ? String(data.original_price) : f.original_price,
        image_url: data.image_url || f.image_url,
        source: data.source || f.source,
      }));
    } catch {
      setParseError("파싱 실패 — 직접 입력하세요");
    } finally {
      setParseLoading(false);
    }
  };

  /* ── Naver 자동완성 ── */
  const handleLookup = async () => {
    if (!lookupQuery.trim()) return;
    setLookupLoading(true);
    setLookupResults([]);
    try {
      const res = await fetch(
        `${API_BASE}/admin/lookup?q=${encodeURIComponent(lookupQuery)}`,
        { headers: { "X-Admin-Key": getAdminKey() } }
      );
      const data = await res.json();
      setLookupResults(data.results || []);
    } catch {
      setError("Naver 조회 실패");
    } finally {
      setLookupLoading(false);
    }
  };

  const applyResult = (r: NaverResult) => {
    setForm((f) => ({
      ...f,
      title: r.title || f.title,
      original_price: r.hprice ? String(r.hprice) : f.original_price,
      sale_price: r.lprice && !f.sale_price ? String(r.lprice) : f.sale_price,
      image_url: r.image || f.image_url,
    }));
    setLookupResults([]);
    setLookupQuery("");
  };

  /* ── 등록 ── */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    const orig = Number(form.original_price);
    const sale = Number(form.sale_price);
    if (sale > 0 && orig <= sale) {
      setError("정가가 할인가보다 낮거나 같습니다");
      setSubmitting(false);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/admin/deals/quick-add`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Admin-Key": getAdminKey(),
        },
        body: JSON.stringify({
          ...form,
          original_price: orig,
          sale_price: sale,
        }),
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || "등록 실패");
      }
      const deal = await res.json();
      setSuccess({ id: deal.id, title: deal.title });
      setForm({
        product_url: "",
        title: "",
        original_price: "",
        sale_price: "",
        category: "",
        image_url: "",
        description: "",
        source: "admin",
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "오류 발생");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto py-8 px-4">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => router.push("/admin")}
          className="text-gray-400 hover:text-gray-700 text-sm"
        >
          ← 대시보드
        </button>
        <h1 className="text-xl font-bold">딜 빠른 등록</h1>
        <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded font-medium">
          검증 없이 바로 active
        </span>
      </div>

      {/* 성공 메시지 */}
      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded text-sm">
          <p className="font-medium text-green-800">✅ 등록 완료 — #{success.id}</p>
          <p className="text-green-600 mt-0.5">{success.title}</p>
          <div className="flex gap-2 mt-2">
            <a
              href={`/deal/${success.id}`}
              target="_blank"
              className="text-xs underline text-green-700"
            >
              딜 보기 →
            </a>
            <button
              onClick={() => setSuccess(null)}
              className="text-xs underline text-green-700"
            >
              다시 등록
            </button>
          </div>
        </div>
      )}

      {/* ── URL 자동 채우기 섹션 ── */}
      <div className="mb-5 p-4 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-xs font-semibold text-blue-700 mb-2 uppercase tracking-wide">
          🔗 URL 붙여넣기 → 자동 채우기
        </p>
        <div className="flex gap-2">
          <input
            type="url"
            placeholder="상품 URL 붙여넣기 (쿠팡·네이버·11번가·G마켓)"
            className="flex-1 border border-blue-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-blue-500 bg-white"
            onPaste={(e) => {
              const pasted = e.clipboardData.getData("text").trim();
              if (!pasted.startsWith("http")) return;
              const u = pasted.toLowerCase();
              const source = u.includes("coupang") ? "coupang"
                : u.includes("naver") ? "naver" : "etc";
              setForm((f) => ({ ...f, product_url: pasted, source }));
              setTimeout(() => handleParseUrl(pasted), 150);
            }}
            value={form.product_url}
            onChange={(e) => {
              const url = e.target.value;
              const u = url.toLowerCase();
              const source = u.includes("coupang") ? "coupang"
                : u.includes("naver") ? "naver" : form.source;
              setForm({ ...form, product_url: url, source });
            }}
          />
          <button
            type="button"
            onClick={() => handleParseUrl()}
            disabled={parseLoading || !form.product_url.startsWith("http")}
            className="px-4 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-40 whitespace-nowrap"
          >
            {parseLoading ? "분석 중…" : "자동 채우기"}
          </button>
        </div>
        {parseError && (
          <div className="mt-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1.5">
            ⚠️ {parseError}
            {parseError.includes("쿠팡") && (
              <span className="block mt-0.5 text-gray-500">
                → 상품명을 아래 Naver 검색에 붙여넣으면 정가를 자동으로 찾습니다
              </span>
            )}
          </div>
        )}
        {!parseError && (
          <p className="mt-1 text-xs text-blue-500">
            붙여넣으면 제목·정가·할인가 자동 입력 (쿠팡은 Naver 검색 이용)
          </p>
        )}
      </div>

      {/* Naver 자동완성 */}
      <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
        <p className="text-xs font-medium text-gray-500 mb-2 uppercase tracking-wide">
          Naver 상품 검색 자동완성
        </p>
        <div className="flex gap-2">
          <input
            type="text"
            placeholder="상품명으로 검색"
            value={lookupQuery}
            onChange={(e) => setLookupQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), handleLookup())}
            className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-gray-500"
          />
          <button
            type="button"
            onClick={handleLookup}
            disabled={lookupLoading}
            className="px-4 py-2 bg-gray-900 text-white text-sm rounded hover:bg-gray-700 disabled:opacity-50"
          >
            {lookupLoading ? "조회 중…" : "검색"}
          </button>
        </div>
        {lookupResults.length > 0 && (
          <ul className="mt-2 border border-gray-200 rounded bg-white divide-y">
            {lookupResults.map((r, i) => (
              <li key={i}>
                <button
                  type="button"
                  onClick={() => applyResult(r)}
                  className="w-full flex items-center gap-3 p-2 hover:bg-gray-50 text-left"
                >
                  {r.image && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={r.image} alt="" className="w-10 h-10 object-cover rounded" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate">{r.title}</p>
                    <p className="text-xs text-gray-500">
                      {r.lprice ? `최저 ${r.lprice.toLocaleString()}원` : ""}
                      {r.hprice ? ` / 정가 ${r.hprice.toLocaleString()}원` : ""}
                    </p>
                  </div>
                  <span className="text-xs text-gray-400 shrink-0">선택 →</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* ── 등록 폼 ── */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* 상품 URL (위 입력과 연동, 확인용) */}
        {form.product_url && (
          <div className="p-2 bg-gray-50 border border-gray-200 rounded text-xs text-gray-500 break-all">
            <span className="font-medium text-gray-700">URL: </span>
            {form.product_url.length > 70
              ? form.product_url.slice(0, 70) + "…"
              : form.product_url}
            {isCoupangDirect && (
              <span className="ml-2 inline-flex items-center gap-1">
                <span className="text-amber-600">⚠ 파트너스 아님</span>
                <a
                  href={`https://partners.coupang.com/#affiliate/ws/link-to-any-page?url=${encodeURIComponent(form.product_url)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-1.5 py-0.5 bg-red-600 text-white rounded hover:bg-red-700"
                >
                  파트너스 변환 →
                </a>
              </span>
            )}
            {isCoupangPartners && (
              <span className="ml-2 text-emerald-600">✅ 파트너스</span>
            )}
          </div>
        )}
        {/* hidden URL field for form submission */}
        <input type="hidden" name="product_url" value={form.product_url} />

        {/* 제목 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            제목 <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            required
            placeholder="[브랜드] 상품명"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-gray-500"
          />
        </div>

        {/* 가격 */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              정가 (원) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              required
              min={1}
              placeholder="48000"
              value={form.original_price}
              onChange={(e) => setForm({ ...form, original_price: e.target.value })}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-gray-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              할인가 (원) <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              required
              min={0}
              placeholder="11990"
              value={form.sale_price}
              onChange={(e) => setForm({ ...form, sale_price: e.target.value })}
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-gray-500"
            />
          </div>
        </div>

        {discountRate !== null && (
          <p className={`text-sm font-medium ${discountRate > 0 ? "text-red-600" : "text-gray-400"}`}>
            {discountRate > 0 ? `→ ${discountRate}% 할인` : "⚠️ 할인 없음 (등록 불가)"}
          </p>
        )}

        {/* 카테고리 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">카테고리</label>
          <select
            value={form.category}
            onChange={(e) => setForm({ ...form, category: e.target.value })}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-gray-500"
          >
            <option value="">자동 감지</option>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        {/* 이미지 URL */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">이미지 URL</label>
          <div className="flex gap-2 items-start">
            <input
              type="url"
              placeholder="https://..."
              value={form.image_url}
              onChange={(e) => setForm({ ...form, image_url: e.target.value })}
              className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-gray-500"
            />
            {form.image_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={form.image_url}
                alt="preview"
                className="w-14 h-14 object-cover rounded border border-gray-200"
                onError={(e) => (e.currentTarget.style.display = "none")}
              />
            )}
          </div>
        </div>

        {/* 소스 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">소스</label>
          <select
            value={form.source}
            onChange={(e) => setForm({ ...form, source: e.target.value })}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:border-gray-500"
          >
            <option value="admin">admin (수동 등록)</option>
            <option value="coupang">coupang</option>
            <option value="naver">naver</option>
            <option value="community">community</option>
          </select>
        </div>

        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
            ⚠️ {error}
          </p>
        )}

        <button
          type="submit"
          disabled={submitting || (discountRate !== null && discountRate <= 0)}
          className="w-full py-3 bg-gray-900 text-white font-medium rounded hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? "등록 중…" : "지금 바로 등록 →"}
        </button>
      </form>
    </div>
  );
}
