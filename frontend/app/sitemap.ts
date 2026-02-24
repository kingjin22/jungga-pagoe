import { MetadataRoute } from "next";
import { CATEGORIES } from "@/lib/categories";

const BASE_URL = "https://jungga-pagoe.vercel.app";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  // 정적 페이지
  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE_URL, lastModified: now, changeFrequency: "hourly", priority: 1.0 },
    { url: `${BASE_URL}/?hot_only=true`, lastModified: now, changeFrequency: "hourly", priority: 0.9 },
  ];

  // 브랜드 페이지
  let brandPages: MetadataRoute.Sitemap = [];
  try {
    const res = await fetch(`${API_BASE}/api/brands`, { next: { revalidate: 3600 } });
    if (res.ok) {
      const brands: { brand: string; slug: string }[] = await res.json();
      brandPages = brands.map((b) => ({
        url: `${BASE_URL}/brand/${b.slug}`,
        lastModified: now,
        changeFrequency: "daily" as const,
        priority: 0.8,
      }));
    }
  } catch {}

  // 카테고리 페이지
  const categoryPages: MetadataRoute.Sitemap = Object.values(CATEGORIES).map((c) => ({
    url: `${BASE_URL}/category/${c.slug}`,
    lastModified: now,
    changeFrequency: "hourly" as const,
    priority: 0.8,
  }));

  // 딜 상세 페이지 (active 딜만)
  let dealPages: MetadataRoute.Sitemap = [];
  try {
    const res = await fetch(`${API_BASE}/api/deals?size=100&sort=discount`, { next: { revalidate: 1800 } });
    if (res.ok) {
      const data: { items: { id: number; updated_at: string }[] } = await res.json();
      dealPages = data.items.map((d) => ({
        url: `${BASE_URL}/deal/${d.id}`,
        lastModified: new Date(d.updated_at),
        changeFrequency: "daily" as const,
        priority: 0.6,
      }));
    }
  } catch {}

  return [...staticPages, ...brandPages, ...categoryPages, ...dealPages];
}
