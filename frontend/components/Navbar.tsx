"use client";

import { Hammer, Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getSupabase } from "@/lib/supabase/client";
import clsx from "clsx";

const links = [
  { href: "/browse", label: "Browse" },
  { href: "/validator", label: "Validator" },
  { href: "/pricing", label: "Pricing" },
];

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [signedIn, setSignedIn] = useState<boolean | null>(null);

  useEffect(() => {
    const supabase = getSupabase();
    supabase.auth
      .getSession()
      .then(({ data }) => setSignedIn(!!data.session))
      .catch(() => setSignedIn(false));
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      setSignedIn(!!session);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  useEffect(() => setOpen(false), [pathname]);

  async function signOut() {
    await getSupabase().auth.signOut();
    router.push("/");
    router.refresh();
  }

  return (
    <header className="sticky top-0 z-40 border-b border-edge bg-base/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Hammer size={18} />
          </span>
          <span className="text-[17px]">ProblemForge</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={clsx(
                "rounded-lg px-3 py-2 text-sm transition",
                pathname.startsWith(link.href)
                  ? "text-ink"
                  : "text-muted hover:text-ink"
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
          {signedIn ? (
            <>
              <Link href="/account" className="btn-ghost px-3.5 py-2">
                Account
              </Link>
              <button onClick={signOut} className="rounded-lg px-3 py-2 text-sm text-muted transition hover:text-ink">
                Sign out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-lg px-3 py-2 text-sm text-muted transition hover:text-ink"
              >
                Sign In
              </Link>
              <Link href="/signup" className="btn-accent px-4 py-2">
                Get Started
              </Link>
            </>
          )}
        </div>

        <button
          className="rounded-lg p-2 text-muted transition hover:text-ink md:hidden"
          onClick={() => setOpen((v) => !v)}
          aria-label="Toggle menu"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {open && (
        <div className="border-t border-edge bg-base px-4 pb-4 pt-2 md:hidden">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="block rounded-lg px-3 py-2.5 text-sm text-ink hover:bg-surface"
            >
              {link.label}
            </Link>
          ))}
          <div className="mt-2 flex flex-col gap-2 border-t border-edge pt-3">
            {signedIn ? (
              <>
                <Link href="/account" className="btn-ghost w-full">
                  Account
                </Link>
                <button onClick={signOut} className="btn-ghost w-full">
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link href="/login" className="btn-ghost w-full">
                  Sign In
                </Link>
                <Link href="/signup" className="btn-accent w-full">
                  Get Started
                </Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
