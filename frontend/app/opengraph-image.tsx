import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "정가파괴 - 브랜드 핫딜 최저가 모음";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "#fff",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "flex-start",
          padding: "80px",
          fontFamily: "sans-serif",
        }}
      >
        {/* 로고 */}
        <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "40px" }}>
          <div
            style={{
              background: "#111",
              color: "#fff",
              fontSize: "28px",
              fontWeight: 900,
              padding: "8px 20px",
              letterSpacing: "-0.5px",
            }}
          >
            정가파괴
          </div>
        </div>

        {/* 메인 카피 */}
        <div
          style={{
            fontSize: "64px",
            fontWeight: 900,
            color: "#111",
            lineHeight: 1.1,
            marginBottom: "24px",
            letterSpacing: "-2px",
          }}
        >
          브랜드 공식 정가 대비
          <br />
          <span style={{ color: "#E31E24" }}>진짜 할인</span>만 모은 곳
        </div>

        {/* 서브 카피 */}
        <div style={{ fontSize: "26px", color: "#888", fontWeight: 400 }}>
          Apple · Samsung · Nike · Dyson · Sony 최저가 실시간 추적
        </div>

        {/* 하단 */}
        <div
          style={{
            position: "absolute",
            bottom: "60px",
            right: "80px",
            fontSize: "20px",
            color: "#bbb",
          }}
        >
          jungga-pagoe.vercel.app
        </div>
      </div>
    ),
    { ...size }
  );
}
