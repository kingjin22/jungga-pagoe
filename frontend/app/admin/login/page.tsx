"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { adminLogin, getAdminMetrics } from "@/lib/admin-api";

export default function AdminLoginPage() {
  const router = useRouter();
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!key.trim()) return;
    setLoading(true);
    setError("");
    try {
      // key를 먼저 저장하고 실제 API 호출로 검증
      if (typeof window !== "undefined") {
        localStorage.setItem("admin_key", key.trim());
      }
      await getAdminMetrics();
      adminLogin(key.trim());
      router.replace("/admin/dashboard");
    } catch {
      if (typeof window !== "undefined") {
        localStorage.removeItem("admin_key");
      }
      setError("인증 실패: 잘못된 Admin Key입니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <p className="text-xs text-gray-400 font-medium uppercase tracking-widest mb-1">
            정가파괴
          </p>
          <h1 className="text-2xl font-black text-gray-900">Admin</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-600 mb-1.5 uppercase tracking-wider">
              Admin Key
            </label>
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              className="w-full border border-gray-200 px-3 py-2.5 text-sm focus:outline-none focus:border-gray-900 transition-colors"
              placeholder="••••••••"
              autoFocus
            />
          </div>

          {error && (
            <p className="text-xs text-[#E31E24] font-medium">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading || !key.trim()}
            className="w-full bg-[#111] text-white font-bold py-2.5 text-sm hover:bg-[#333] transition-colors disabled:opacity-40"
          >
            {loading ? "확인 중..." : "로그인"}
          </button>
        </form>
      </div>
    </div>
  );
}
