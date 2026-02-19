import { MetadataRoute } from "next";

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
  let categoryPages: MetadataRoute.Sitemap = [];
  try {
    const res = await fetch(`${API_BASE}/api/categories`, { next: { revalidate: 3600 } });
    if (res.ok) {
      const cats: { category: string }[] = await res.json();
      categoryPages = cats.map((c) => ({
        url: `${BASE_URL}/?category=${encodeURIComponent(c.category)}`,
        lastModified: now,
        changeFrequency: "daily" as const,
        priority: 0.7,
      }));
    }
  } catch {}

  return [...staticPages, ...brandPages, ...categoryPages];
}
