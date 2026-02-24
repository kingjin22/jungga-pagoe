import { ImageResponse } from "next/og";

export const runtime = "edge";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let title = "정가파괴 핫딜";
  let price = "";
  let discount = "";
  let category = "";
  let imageUrl = "";

  try {
    const res = await fetch(`${API_BASE}/api/deals/${id}`);
    if (res.ok) {
      const deal = await res.json();
      title = deal.title.replace(/^\[[^\]]+\]\s*/, ""); // [브랜드] 제거
      price = deal.sale_price > 0
        ? new Intl.NumberFormat("ko-KR").format(deal.sale_price) + "원"
        : "무료";
      discount = deal.discount_rate > 0 ? `-${Math.round(deal.discount_rate)}%` : "";
      category = deal.category || "";
      imageUrl = deal.image_url || "";
    }
  } catch {}

  return new ImageResponse(
    (
      <div
        style={{
          background: "#fff",
          width: "100%",
          height: "100%",
          display: "flex",
          fontFamily: "sans-serif",
        }}
      >
        {/* 왼쪽: 제품 이미지 */}
        {imageUrl && (
          <div
            style={{
              width: "400px",
              height: "100%",
              background: "#f5f5f5",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              flexShrink: 0,
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={imageUrl}
              alt={title}
              style={{ width: "320px", height: "320px", objectFit: "contain" }}
            />
          </div>
        )}

        {/* 오른쪽: 텍스트 */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            padding: "60px",
          }}
        >
          {/* 카테고리 */}
          {category && (
            <div style={{ fontSize: "20px", color: "#999", marginBottom: "16px" }}>
              {category}
            </div>
          )}

          {/* 제목 */}
          <div
            style={{
              fontSize: title.length > 30 ? "32px" : "40px",
              fontWeight: 900,
              color: "#111",
              lineHeight: 1.3,
              marginBottom: "32px",
            }}
          >
            {title.length > 50 ? title.slice(0, 50) + "…" : title}
          </div>

          {/* 가격 + 할인율 */}
          <div style={{ display: "flex", alignItems: "baseline", gap: "16px" }}>
            {discount && (
              <div
                style={{
                  fontSize: "48px",
                  fontWeight: 900,
                  color: "#E31E24",
                }}
              >
                {discount}
              </div>
            )}
            <div style={{ fontSize: "48px", fontWeight: 900, color: "#111" }}>
              {price}
            </div>
          </div>

          {/* 브랜드 */}
          <div
            style={{
              marginTop: "32px",
              fontSize: "20px",
              color: "#bbb",
              borderTop: "1px solid #eee",
              paddingTop: "24px",
            }}
          >
            정가파괴 — 공식 정가 대비 진짜 할인만
          </div>
        </div>
      </div>
    ),
    { ...size }
  );
}
