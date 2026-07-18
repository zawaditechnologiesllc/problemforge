import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Idea Validator",
  description:
    "Validate your app idea against decades of expired patents, real community demand, and the 5-Point Validation Framework — free to try.",
  alternates: { canonical: "/validator" },
};

export default function ValidatorLayout({ children }: { children: React.ReactNode }) {
  return children;
}
