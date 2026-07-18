import Link from "next/link";
import { POLICIES_EFFECTIVE_DATE, POLICY_LINKS } from "@/lib/site";

export function PolicyPage({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-12 sm:px-6 sm:py-16">
      <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
      <p className="mt-2 text-sm text-muted">
        Effective date: {POLICIES_EFFECTIVE_DATE}
      </p>
      <div className="prose-policy mt-8 space-y-6 text-[15px] leading-relaxed text-ink/90">
        {children}
      </div>
      <div className="mt-12 border-t border-edge pt-6">
        <p className="section-label mb-3">All policies</p>
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
          {POLICY_LINKS.map((link) => (
            <Link key={link.href} href={link.href} className="text-accent">
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}

export function Section({
  heading,
  children,
}: {
  heading: string;
  children: React.ReactNode;
}) {
  return (
    <section>
      <h2 className="mb-2 text-lg font-semibold tracking-tight text-ink">
        {heading}
      </h2>
      <div className="space-y-3 text-muted">{children}</div>
    </section>
  );
}
