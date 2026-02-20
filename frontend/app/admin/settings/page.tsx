"use client";
import { useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";
const KEY = process.env.NEXT_PUBLIC_ADMIN_KEY || "";

export default function AdminSettings() {
  const [token, setToken] = useState("");
  const [cookie, setCookie] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; message: string; test_link?: string } | null>(null);
  const [adminKey, setAdminKey] = useState("");

  async function handleSave() {
    const key = adminKey || KEY;
    if (!key) { alert("어드민 키를 입력하세요"); return; }
    if (!token.trim()) { alert("토큰을 입력하세요"); return; }
    setLoading(true);
    setResult(null);
    try {
      const r = await fetch(`${API}/admin/update-coupang-token`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Admin-Key": key },
        body: JSON.stringify({ token: token.trim(), cookie: cookie.trim() }),
      });
      const data = await r.json();
      if (r.ok) setResult({ ok: true, message: data.message, test_link: data.test_link });
      else setResult({ ok: false, message: data.detail || "오류 발생" });
    } catch (e) {
      setResult({ ok: false, message: "네트워크 오류" });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto p-6">
        <div className="flex items-center gap-3 mb-6">
          <Link href="/admin" className="text-gray-500 hover:text-gray-900 text-sm">← 어드민</Link>
          <h1 className="text-xl font-bold text-gray-900">설정</h1>
        </div>

        {/* 쿠팡 파트너스 토큰 갱신 */}
        <div className="bg-white rounded border border-gray-200 p-5 mb-6">
          <h2 className="font-semibold text-gray-800 mb-1">쿠팡 파트너스 토큰 갱신</h2>
          <p className="text-xs text-gray-500 mb-4">
            세션 만료 시 partners.coupang.com 로그인 후 콘솔에서{" "}
            <code className="bg-gray-100 px-1 rounded">window.xToken</code>을 복사해 붙여넣기
          </p>

          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                어드민 키
              </label>
              <input
                type="password"
                placeholder="jungga2026admin"
                value={adminKey}
                onChange={(e) => setAdminKey(e.target.value)}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                xToken <span className="text-red-500">*</span>
              </label>
              <textarea
                placeholder="window.xToken 값 붙여넣기..."
                value={token}
                onChange={(e) => setToken(e.target.value)}
                rows={3}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Cookie <span className="text-gray-400 text-xs">(선택)</span>
              </label>
              <textarea
                placeholder="document.cookie 값 (선택 사항)"
                value={cookie}
                onChange={(e) => setCookie(e.target.value)}
                rows={2}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm font-mono"
              />
            </div>
            <button
              onClick={handleSave}
              disabled={loading}
              className="bg-gray-900 text-white px-5 py-2 rounded text-sm font-medium hover:bg-gray-700 disabled:opacity-50"
            >
              {loading ? "저장 중..." : "저장 및 테스트"}
            </button>
          </div>

          {result && (
            <div className={`mt-4 p-3 rounded text-sm ${result.ok ? "bg-green-50 text-green-800" : "bg-red-50 text-red-800"}`}>
              <p className="font-medium">{result.ok ? "✅" : "❌"} {result.message}</p>
              {result.test_link && (
                <p className="mt-1 text-xs">
                  테스트 링크:{" "}
                  <a href={result.test_link} target="_blank" className="underline">{result.test_link}</a>
                </p>
              )}
            </div>
          )}
        </div>

        {/* 토큰 갱신 방법 */}
        <div className="bg-blue-50 border border-blue-100 rounded p-4 text-sm text-blue-800">
          <p className="font-semibold mb-2">토큰 갱신 방법</p>
          <ol className="list-decimal list-inside space-y-1 text-xs">
            <li>Chrome에서 <a href="https://partners.coupang.com" target="_blank" className="underline">partners.coupang.com</a> 로그인</li>
            <li>F12 개발자도구 → Console 탭 열기</li>
            <li><code className="bg-blue-100 px-1 rounded">window.xToken</code> 입력 후 Enter</li>
            <li>출력된 값 전체 복사 → 위 xToken 칸에 붙여넣기</li>
            <li>저장 및 테스트 클릭</li>
          </ol>
        </div>
      </div>
    </div>
  );
}
