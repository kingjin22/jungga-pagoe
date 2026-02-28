import { MetadataRoute } from "next";
import { CATEGORIES } from "@/lib/categories";

const BASE_URL = "https://jungga-pagoe.vercel.app";
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://jungga-pagoe-production.up.railway.app";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  // 정적 페이지
  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE_URL, lastModified: now, changeFrequency: "hourly", priority: 1.0 },
    { url: `${BASE_URL}/?hot_only=true`, lastModified: now, changeFrequency: "hourly", priority: 0.9 },
    { url: `${BASE_URL}/weekly-top`, lastModified: now, changeFrequency: "daily", priority: 0.85 },
    { url: `${BASE_URL}/group-buy`, lastModified: now, changeFrequency: "hourly", priority: 0.8 },
    { url: `${BASE_URL}/gifticon`, lastModified: now, changeFrequency: "hourly", priority: 0.8 },
    { url: `${BASE_URL}/raffle`, lastModified: now, changeFrequency: "daily", priority: 0.75 },
    { url: `${BASE_URL}/coupon`, lastModified: now, changeFrequency: "hourly", priority: 0.8 },
    { url: `${BASE_URL}/preorder`, lastModified: now, changeFrequency: "daily", priority: 0.75 },
    { url: `${BASE_URL}/timedeal`, lastModified: now, changeFrequency: "hourly", priority: 0.8 },
    { url: `${BASE_URL}/fashion`, lastModified: now, changeFrequency: "hourly", priority: 0.8 },
    { url: `${BASE_URL}/electronics`, lastModified: now, changeFrequency: "hourly" as const, priority: 0.8 },
    { url: `${BASE_URL}/electronics`, lastModified: now, changeFrequency: "hourly" as const, priority: 0.8 },
    { url: `${BASE_URL}/search`, lastModified: now, changeFrequency: "daily", priority: 0.7 },
    // 소스별 페이지
    { url: `${BASE_URL}/source/clien`, lastModified: now, changeFrequency: "hourly", priority: 0.75 },
    { url: `${BASE_URL}/source/ruliweb`, lastModified: now, changeFrequency: "hourly", priority: 0.75 },
    { url: `${BASE_URL}/source/quasarzone`, lastModified: now, changeFrequency: "hourly", priority: 0.75 },
    { url: `${BASE_URL}/source/naver`, lastModified: now, changeFrequency: "hourly", priority: 0.7 },
    { url: `${BASE_URL}/source/community`, lastModified: now, changeFrequency: "hourly", priority: 0.7 },
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
    const res = await fetch(`${API_BASE}/api/deals/?limit=500&status=active`, { next: { revalidate: 1800 } });
    if (res.ok) {
      const data: { items: { id: number; updated_at: string; discount_rate: number }[] } = await res.json();
      dealPages = data.items.map((d) => ({
        url: `${BASE_URL}/deal/${d.id}`,
        lastModified: new Date(d.updated_at),
        changeFrequency: "daily" as const,
        priority: d.discount_rate >= 30 ? 0.9 : 0.7,
      }));
    }
  } catch {}

  return [...staticPages, ...brandPages, ...categoryPages, ...dealPages];
}
