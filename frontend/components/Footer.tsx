import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-edge">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="font-semibold">ProblemForge</p>
          <p className="mt-1 max-w-md text-sm text-muted">
            Validated startup problems mined from expired, public-domain
            patents. Informational only — not legal advice.
          </p>
        </div>
        <nav className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted">
          <Link href="/browse" className="transition hover:text-ink">Browse</Link>
          <Link href="/validator" className="transition hover:text-ink">Validator</Link>
          <Link href="/pricing" className="transition hover:text-ink">Pricing</Link>
          <Link href="/account" className="transition hover:text-ink">Account</Link>
        </nav>
      </div>
      <div className="border-t border-edge py-4 text-center text-xs text-muted">
        © {new Date().getFullYear()} ProblemForge. All rights reserved.
      </div>
    </footer>
  );
}
