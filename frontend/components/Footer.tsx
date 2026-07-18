import Link from "next/link";
import { POLICY_LINKS } from "@/lib/site";

export function Footer() {
  return (
    <footer className="border-t border-edge">
      <div className="mx-auto flex max-w-6xl flex-col gap-8 px-4 py-10 sm:px-6 md:flex-row md:justify-between">
        <div className="max-w-sm">
          <p className="font-semibold">ProblemForge</p>
          <p className="mt-1 text-sm text-muted">
            Validated startup problems mined from expired, public-domain
            patents across 20 regions. Informational only — not legal advice.
          </p>
        </div>
        <div className="flex flex-col gap-8 sm:flex-row sm:gap-16">
          <nav aria-label="Product">
            <p className="section-label mb-3">Product</p>
            <div className="flex flex-col gap-2 text-sm text-muted">
              <Link href="/browse" className="transition hover:text-ink">Browse</Link>
              <Link href="/validator" className="transition hover:text-ink">Validator</Link>
              <Link href="/pricing" className="transition hover:text-ink">Pricing</Link>
              <Link href="/account" className="transition hover:text-ink">Account</Link>
            </div>
          </nav>
          <nav aria-label="Legal">
            <p className="section-label mb-3">Legal</p>
            <div className="flex flex-col gap-2 text-sm text-muted">
              {POLICY_LINKS.map((link) => (
                <Link key={link.href} href={link.href} className="transition hover:text-ink">
                  {link.label}
                </Link>
              ))}
            </div>
          </nav>
        </div>
      </div>
      <div className="border-t border-edge py-4 text-center text-xs text-muted">
        © {new Date().getFullYear()} ProblemForge. All rights reserved.
      </div>
    </footer>
  );
}
