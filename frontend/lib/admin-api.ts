const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

function getAdminKey(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("admin_key") || "";
}

async function adminFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const key = getAdminKey();
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": key,
      "Cache-Control": "no-cache",
      ...(options.headers || {}),
    },
  });
  if (res.status === 401 || res.status === 403) {
    if (typeof window !== "undefined") {
      window.location.href = "/admin/login";
    }
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail || `HTTP ${res.status}`);
  }
  return res.json() as Promise<T>;
}

// ── Types ──────────────────────────────────

export interface AdminMetrics {
  date: string;
  today: {
    pv: number;
    impressions?: number;
    clicks: number;
    deal_opens: number;
    active_deals: number;
    new_deals: number;
  };
  trend: Array<{
    date: string;
    pv: number;
    clicks: number;
    deal_opens: number;
  }>;
  top10: Array<{
    id: number;
    title: string;
    sale_price: number;
    discount_rate: number;
    source: string;
    upvotes: number;
    clicks_today: number;
  }>;
}

export interface AdminDeal {
  id: number;
  title: string;
  sale_price: number;
  original_price: number;
  discount_rate: number;
  image_url?: string;
  product_url: string;
  affiliate_url?: string;
  source: string;
  category: string;
  brand?: string;
  status: string;
  is_hot: boolean;
  pinned?: boolean;
  admin_note?: string;
  expires_at?: string;
  upvotes: number;
  views: number;
  report_count?: number;
  submitter_name?: string;
  created_at: string;
  updated_at: string;
  today_views?: number;
  total_views?: number;
  today_clicks?: number;
  total_clicks?: number;
  last_scraped_at?: string;
  // detail only
  price_history?: Array<{ checked_at: string; price: number }>;
  stats_today?: { impressions: number; deal_opens: number; clicks: number };
}

export interface AdminDealsResponse {
  items: AdminDeal[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface AdminDealPatch {
  status?: string;
  pinned?: boolean;
  admin_note?: string;
  expires_at?: string;
  is_hot?: boolean;
}

// ── API calls ─────────────────────────────

export async function getAdminMetrics(date?: string): Promise<AdminMetrics> {
  const q = date ? `?date=${date}` : "";
  return adminFetch<AdminMetrics>(`/admin/metrics${q}`);
}

export async function getAdminDeals(params?: {
  status?: string;
  source?: string;
  search?: string;
  pinned?: boolean;
  sort?: string;
  page?: number;
  size?: number;
}): Promise<AdminDealsResponse> {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.source) q.set("source", params.source);
  if (params?.search) q.set("search", params.search);
  if (params?.pinned !== undefined) q.set("pinned", String(params.pinned));
  if (params?.sort) q.set("sort", params.sort);
  if (params?.page) q.set("page", String(params.page));
  if (params?.size) q.set("size", String(params.size));
  return adminFetch<AdminDealsResponse>(`/admin/deals?${q}`);
}

export async function getAdminDeal(id: number): Promise<AdminDeal> {
  return adminFetch<AdminDeal>(`/admin/deals/${id}`);
}

export async function patchAdminDeal(
  id: number,
  data: AdminDealPatch
): Promise<AdminDeal> {
  return adminFetch<AdminDeal>(`/admin/deals/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function rescrapeAdminDeal(
  id: number
): Promise<{ status: string; source: string; message?: string }> {
  return adminFetch(`/admin/deals/${id}/rescrape`, { method: "POST" });
}

export function adminLogin(key: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem("admin_key", key);
  }
}

export function adminLogout(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem("admin_key");
    window.location.href = "/admin/login";
  }
}

export function isAdminLoggedIn(): boolean {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("admin_key");
}
