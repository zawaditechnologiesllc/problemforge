import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

const STATIC_PAGES: { path: string; priority: number; freq: "daily" | "weekly" | "monthly" }[] = [
  { path: "", priority: 1.0, freq: "daily" },
  { path: "/browse", priority: 0.9, freq: "daily" },
  { path: "/validator", priority: 0.8, freq: "weekly" },
  { path: "/pricing", priority: 0.8, freq: "weekly" },
  { path: "/terms", priority: 0.3, freq: "monthly" },
  { path: "/privacy", priority: 0.3, freq: "monthly" },
  { path: "/refunds", priority: 0.3, freq: "monthly" },
  { path: "/acceptable-use", priority: 0.3, freq: "monthly" },
  { path: "/disclaimer", priority: 0.3, freq: "monthly" },
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = STATIC_PAGES.map((page) => ({
    url: `${SITE_URL}${page.path || "/"}`,
    changeFrequency: page.freq,
    priority: page.priority,
  }));

  // Every blueprint page is a long-tail SEO landing page — include up to 500.
  try {
    for (let offset = 0; offset < 500; offset += 50) {
      const response = await fetch(
        `${API_URL}/api/v1/blueprints?limit=50&offset=${offset}&sort=newest`,
        { next: { revalidate: 3600 } }
      );
      if (!response.ok) break;
      const data = await response.json();
      const items: { id: string; created_at: string }[] = data.items ?? [];
      for (const item of items) {
        entries.push({
          url: `${SITE_URL}/blueprint/${item.id}`,
          lastModified: item.created_at,
          changeFrequency: "weekly",
          priority: 0.7,
        });
      }
      if (items.length < 50) break;
    }
  } catch {
    // API unreachable during build — static pages still ship.
  }
  return entries;
}
