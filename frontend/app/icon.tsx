import { ImageResponse } from "next/og";

export const size = { width: 192, height: 192 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    <div
      style={{
        background: "#E31E24",
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: 96,
        color: "white",
        fontWeight: 900,
        fontFamily: "serif",
      }}
    >
      정
    </div>,
    { ...size }
  );
}
