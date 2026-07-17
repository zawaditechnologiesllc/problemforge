import Link from "next/link";
import { ArrowRight, FileSearch, Sparkles, Terminal } from "lucide-react";
import { BlueprintCard } from "@/components/BlueprintCard";
import { HomeSearch } from "@/components/HomeSearch";
import { API_URL } from "@/lib/api";
import type { BlueprintSummary } from "@/lib/types";

export const revalidate = 120;

async function getFeatured(): Promise<BlueprintSummary[]> {
  try {
    const response = await fetch(
      `${API_URL}/api/v1/blueprints?sort=buildability&limit=6`,
      { next: { revalidate: 120 } }
    );
    if (!response.ok) return [];
    const data = await response.json();
    return data.items ?? [];
  } catch {
    return [];
  }
}

const steps = [
  {
    icon: FileSearch,
    title: "We mine expired patents",
    body: "Every week we ingest patents that have aged into the public domain — 20+ years old or lapsed for non-payment. Nothing active ever surfaces.",
  },
  {
    icon: Sparkles,
    title: "AI translates them into problems",
    body: "Legal jargon becomes a scannable Idea Blueprint: the human frustration, the now-free core logic, and a modern build plan.",
  },
  {
    icon: Terminal,
    title: "You build the MVP today",
    body: "Copy the master prompt into Cursor or Windsurf and ship a modern version of a validated, once-patented idea.",
  },
];

export default async function HomePage() {
  const featured = await getFeatured();

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(242,169,59,0.08),transparent_55%)]"
        />
        <div className="relative mx-auto max-w-4xl px-4 pb-14 pt-16 text-center sm:px-6 sm:pt-24">
          <p className="mx-auto inline-flex items-center gap-2 rounded-full border border-edge bg-surface px-3.5 py-1.5 text-xs text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-teal" />
            Every idea backed by real, public-domain engineering
          </p>
          <h1 className="mt-6 text-4xl font-bold leading-[1.08] tracking-tight sm:text-6xl">
            Find Validated Problems from{" "}
            <span className="text-accent">Expired Patents.</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-muted sm:text-lg">
            Someone already proved these problems were worth solving — then the
            patent expired. ProblemForge translates that public-domain logic
            into Idea Blueprints you can build with AI, today.
          </p>
          <div className="mx-auto mt-9 max-w-2xl">
            <HomeSearch />
          </div>
        </div>
      </section>

      {/* Featured blueprints */}
      <section className="mx-auto max-w-6xl px-4 pb-20 sm:px-6">
        <div className="mb-6 flex items-end justify-between">
          <div>
            <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
              Fresh Idea Blueprints
            </h2>
            <p className="mt-1 text-sm text-muted">
              Highest AI-buildability picks from the forge.
            </p>
          </div>
          <Link
            href="/browse"
            className="hidden items-center gap-1.5 text-sm font-medium text-accent sm:inline-flex"
          >
            Browse all <ArrowRight size={15} />
          </Link>
        </div>

        {featured.length > 0 ? (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {featured.map((blueprint) => (
              <BlueprintCard key={blueprint.id} blueprint={blueprint} />
            ))}
          </div>
        ) : (
          <div className="card p-10 text-center text-sm text-muted">
            Blueprints are loading into the forge. Connect the API and seed the
            database, then refresh — or head to{" "}
            <Link href="/browse" className="text-accent">Browse</Link>.
          </div>
        )}

        <div className="mt-8 text-center sm:hidden">
          <Link href="/browse" className="btn-ghost w-full">
            Browse all blueprints <ArrowRight size={15} />
          </Link>
        </div>
      </section>

      {/* How it works */}
      <section className="border-t border-edge bg-surface/40">
        <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
          <h2 className="text-center text-xl font-semibold tracking-tight sm:text-2xl">
            From dusty filing to running MVP
          </h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {steps.map(({ icon: Icon, title, body }) => (
              <div key={title} className="card p-6">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-accent-soft text-accent">
                  <Icon size={19} />
                </span>
                <h3 className="mt-4 font-semibold">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA band */}
      <section className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <div className="card relative overflow-hidden p-8 text-center sm:p-12">
          <div
            aria-hidden
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_bottom,rgba(45,212,191,0.07),transparent_60%)]"
          />
          <h2 className="relative text-2xl font-bold tracking-tight sm:text-3xl">
            Stop guessing what to build.
          </h2>
          <p className="relative mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted sm:text-base">
            Validate your idea against 20 years of expired innovation, or pick a
            blueprint and paste the master prompt into Cursor.
          </p>
          <div className="relative mt-7 flex flex-col justify-center gap-3 sm:flex-row">
            <Link href="/signup" className="btn-accent px-6 py-3">
              Get Started Free
            </Link>
            <Link href="/validator" className="btn-ghost px-6 py-3">
              Try the Validator
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
