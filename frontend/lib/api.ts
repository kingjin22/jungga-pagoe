const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Deal {
  id: number;
  title: string;
  description?: string;
  original_price: number;
  sale_price: number;
  discount_rate: number;
  image_url?: string;
  product_url: string;
  affiliate_url?: string;
  source: "coupang" | "naver" | "community";
  category: string;
  status: "active" | "expired" | "price_changed" | "pending";
  upvotes: number;
  views: number;
  is_hot: boolean;
  submitter_name?: string;
  expires_at?: string;
  verified_price?: number;      // 마지막 검증된 실제 가격
  last_verified_at?: string;    // 마지막 검증 시각
  created_at: string;
  updated_at: string;
}

export interface DealListResponse {
  items: Deal[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface DealSubmit {
  title: string;
  original_price: number;
  sale_price: number;
  product_url: string;
  image_url?: string;
  category: string;
  description?: string;
  submitter_name?: string;
}

export async function getDeals(params?: {
  page?: number;
  size?: number;
  category?: string;
  source?: string;
  sort?: string;
  search?: string;
  hot_only?: boolean;
}): Promise<DealListResponse> {
  const query = new URLSearchParams();
  if (params?.page) query.set("page", String(params.page));
  if (params?.size) query.set("size", String(params.size));
  if (params?.category) query.set("category", params.category);
  if (params?.source) query.set("source", params.source);
  if (params?.sort) query.set("sort", params.sort);
  if (params?.search) query.set("search", params.search);
  if (params?.hot_only) query.set("hot_only", "true");

  const res = await fetch(`${API_BASE}/api/deals?${query}`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error("딜 목록 불러오기 실패");
  return res.json();
}

export async function getHotDeals(): Promise<Deal[]> {
  const res = await fetch(`${API_BASE}/api/deals/hot`, {
    next: { revalidate: 30 },
  });
  if (!res.ok) throw new Error("핫딜 불러오기 실패");
  return res.json();
}

export async function upvoteDeal(id: number): Promise<{ upvotes: number; is_hot: boolean }> {
  const res = await fetch(`${API_BASE}/api/deals/${id}/upvote`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("추천 실패");
  return res.json();
}

export async function submitDeal(data: DealSubmit): Promise<Deal> {
  const res = await fetch(`${API_BASE}/api/deals/submit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "제보 실패");
  }
  return res.json();
}

export function formatPrice(price: number): string {
  return price.toLocaleString("ko-KR") + "원";
}

export function getSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    coupang: "쿠팡",
    naver: "네이버",
    community: "커뮤니티",
  };
  return labels[source] || source;
}

export function getSourceColor(source: string): string {
  const colors: Record<string, string> = {
    coupang: "bg-orange-500",
    naver: "bg-green-600",
    community: "bg-blue-600",
  };
  return colors[source] || "bg-gray-500";
}

export interface Stats {
  total_deals: number;
  hot_deals: number;
  by_source: { coupang: number; naver: number; community: number };
  today_added: number;
  avg_discount: number;
}

export async function getStats(): Promise<Stats> {
  const res = await fetch(`${API_BASE}/api/stats`, {
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new Error("통계 불러오기 실패");
  return res.json();
}

export interface CategoryItem {
  category: string;
  count: number;
}

export async function getCategories(): Promise<CategoryItem[]> {
  const res = await fetch(`${API_BASE}/api/categories`, {
    next: { revalidate: 120 },
  });
  if (!res.ok) return [];
  return res.json();
}
