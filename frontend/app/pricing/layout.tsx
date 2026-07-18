import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Browse free forever. Builder ($19/mo) unlocks build plans and master prompts; Pro ($49/mo) adds the developer API; Enterprise ($150/mo) is unlimited. Freedom-to-Operate reports $99.",
  alternates: { canonical: "/pricing" },
};

export default function PricingLayout({ children }: { children: React.ReactNode }) {
  return children;
}
