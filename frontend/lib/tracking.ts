const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

type EventType = "impression" | "deal_open" | "outbound_click";

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let sid = sessionStorage.getItem("_sid");
  if (!sid) {
    sid = Math.random().toString(36).slice(2) + Date.now().toString(36);
    sessionStorage.setItem("_sid", sid);
  }
  return sid;
}

export async function trackEvent(
  type: EventType,
  dealId: number
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
        deal_id: dealId,
        session_id: getSessionId(),
        referrer: referrer || null,
      }),
      // fire-and-forget: don't block UI
      keepalive: true,
    });
  } catch {
    // silently ignore tracking errors
  }
}
