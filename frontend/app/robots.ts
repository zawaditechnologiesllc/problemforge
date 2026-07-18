import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/site";

// Search engines AND AI crawlers are explicitly welcome on public content
// (SEO + AEO/GEO); account, admin, and auth flows are kept out of indexes.
const PRIVATE_PATHS = [
  "/account",
  "/admin",
  "/auth/",
  "/forgot-password",
  "/reset-password",
];

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: "/", disallow: PRIVATE_PATHS },
      {
        userAgent: [
          "GPTBot",
          "OAI-SearchBot",
          "ChatGPT-User",
          "ClaudeBot",
          "Claude-Web",
          "anthropic-ai",
          "PerplexityBot",
          "Google-Extended",
          "CCBot",
          "cohere-ai",
          "meta-externalagent",
        ],
        allow: "/",
        disallow: PRIVATE_PATHS,
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
