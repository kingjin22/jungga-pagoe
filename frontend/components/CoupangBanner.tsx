"use client";

// 쿠팡 파트너스 배너 (728×90)
export default function CoupangBanner() {
  return (
    <div className="flex justify-center my-6">
      <iframe
        src="https://ads-partners.coupang.com/widgets.html?id=966413&template=banner&trackingCode=AF6012567&subId=&width=728&height=90"
        width="728"
        height="90"
        frameBorder="0"
        scrolling="no"
        referrerPolicy="unsafe-url"
        // @ts-expect-error browsingtopics is not in React types
        browsingtopics="true"
        title="쿠팡 파트너스"
        style={{ maxWidth: "100%" }}
      />
    </div>
  );
}
