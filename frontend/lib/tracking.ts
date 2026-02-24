const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";

type EventType = "impression" | "deal_open" | "outbound_click" | "page_view";

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let sid = sessionStorage.getItem("_sid");
  if (!sid) {
    sid = Math.random().toString(36).slice(2) + Date.now().toString(36);
    sessionStorage.setItem("_sid", sid);
  }
  return sid;
}

export async function trackPageView(): Promise<void> {
  if (typeof window === "undefined") return;
  // 세션당 1회만 기록
  if (sessionStorage.getItem("_pv_tracked")) return;
  sessionStorage.setItem("_pv_tracked", "1");
  await trackEvent("page_view", null);
}

export async function trackEvent(
  type: EventType,
  dealId: number | null
): Promise<void> {
  if (typeof window === "undefined") return;
  try {
    const referrer =
      typeof document !== "undefined" ? document.referrer : "";
    await fetch(`${API_BASE}/api/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        event_type: type,
        deal_id: dealId || null,  // 0이나 null 모두 null로
        session_id: getSessionId(),
        referrer: referrer || null,
      }),
      keepalive: true,
    });
  } catch {
    // silently ignore tracking errors
  }
}
