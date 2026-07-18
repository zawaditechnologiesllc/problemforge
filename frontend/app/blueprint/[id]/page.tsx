import type { Metadata } from "next";
import { BlueprintView } from "@/components/BlueprintView";
import { OPERATOR_NAME, SITE_NAME, SITE_URL } from "@/lib/site";
import type { BlueprintDetail } from "@/lib/types";

// Server-rendered shell: crawlers (Google + AI assistants) get the full
// public content, metadata, and structured data without executing JS. The
// client BlueprintView then applies the signed-in context.

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

async function fetchPublicDetail(id: string): Promise<BlueprintDetail | null> {
  if (!/^[0-9a-f-]{36}$/i.test(id)) return null;
  try {
    const response = await fetch(`${API_URL}/api/v1/blueprints/${id}`, {
      next: { revalidate: 300 },
    });
    if (!response.ok) return null;
    return (await response.json()) as BlueprintDetail;
  } catch {
    return null;
  }
}

export async function generateMetadata({
  params,
}: {
  params: { id: string };
}): Promise<Metadata> {
  const blueprint = await fetchPublicDetail(params.id);
  if (!blueprint) {
    return { title: "Idea Blueprint", robots: { index: false } };
  }
  const description = blueprint.human_problem.slice(0, 155).trimEnd() + "…";
  const title = `${blueprint.title} — Idea Blueprint`;
  return {
    title,
    description,
    alternates: { canonical: `/blueprint/${params.id}` },
    openGraph: {
      title,
      description,
      type: "article",
      url: `${SITE_URL}/blueprint/${params.id}`,
      siteName: SITE_NAME,
    },
    twitter: { card: "summary_large_image", title, description },
  };
}

export default async function BlueprintPage({
  params,
}: {
  params: { id: string };
}) {
  const initial = await fetchPublicDetail(params.id);

  const jsonLd = initial
    ? [
        {
          "@context": "https://schema.org",
          "@type": "TechArticle",
          headline: initial.title,
          description: initial.human_problem.slice(0, 300),
          url: `${SITE_URL}/blueprint/${params.id}`,
          datePublished: initial.created_at,
          author: { "@type": "Organization", name: SITE_NAME },
          publisher: { "@type": "Organization", name: OPERATOR_NAME },
          ...(initial.patent_number
            ? {
                isBasedOn: {
                  "@type": "CreativeWork",
                  name: `Patent ${initial.patent_number} (public domain)`,
                },
              }
            : {}),
        },
        {
          "@context": "https://schema.org",
          "@type": "BreadcrumbList",
          itemListElement: [
            { "@type": "ListItem", position: 1, name: "Browse", item: `${SITE_URL}/browse` },
            {
              "@type": "ListItem",
              position: 2,
              name: initial.title,
              item: `${SITE_URL}/blueprint/${params.id}`,
            },
          ],
        },
      ]
    : null;

  return (
    <>
      {jsonLd && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      )}
      <BlueprintView id={params.id} initial={initial} />
    </>
  );
}
