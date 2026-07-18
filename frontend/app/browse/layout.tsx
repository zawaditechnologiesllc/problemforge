import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Browse Idea Blueprints",
  description:
    "Search validated startup ideas mined from expired, public-domain patents — filter by human problem, domain, and AI buildability.",
  alternates: { canonical: "/browse" },
};

export default function BrowseLayout({ children }: { children: React.ReactNode }) {
  return children;
}
