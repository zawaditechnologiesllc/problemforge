"use client";

import { ArrowRight, Loader2, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { DomainBadge } from "@/components/Badges";
import { validateIdea } from "@/lib/api";
import type { ValidatorMatch } from "@/lib/types";

function SimilarityBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div>
      <div className="flex items-center justify-between text-xs text-muted">
        <span>Similarity</span>
        <span className="font-semibold text-teal">{pct}%</span>
      </div>
      <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-raised">
        <div
          className="h-full rounded-full bg-gradient-to-r from-teal/70 to-teal"
          style={{ width: `${Math.max(4, pct)}%` }}
        />
      </div>
    </div>
  );
}

export default function ValidatorPage() {
  const [idea, setIdea] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matches, setMatches] = useState<ValidatorMatch[] | null>(null);

  async function run(event: React.FormEvent) {
    event.preventDefault();
    if (idea.trim().length < 10 || loading) return;
    setLoading(true);
    setError(null);
    setMatches(null);
    try {
      const result = await validateIdea(idea.trim());
      setMatches(result.matches);
    } catch (err: any) {
      setError(err?.message ?? "Validation failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  const primary = matches?.[0];
  const secondary = matches?.slice(1) ?? [];

  return (
    <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-16">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Validate Your Idea Against{" "}
          <span className="text-accent">20 Years of Expired Innovation.</span>
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-sm leading-relaxed text-muted sm:text-base">
          Paste your app idea. We embed it and search every Idea Blueprint for
          expired patents that already solved the same human problem — logic
          you can legally borrow.
        </p>
      </div>

      <form onSubmit={run} className="mt-9">
        <textarea
          className="input min-h-[140px] resize-y rounded-xl text-[15px] leading-relaxed"
          placeholder="Type your app idea here (e.g., 'An app that summarizes legal contracts for freelance designers')..."
          value={idea}
          onChange={(event) => setIdea(event.target.value)}
          maxLength={2000}
        />
        <div className="mt-4 flex flex-col items-center gap-3 sm:flex-row sm:justify-between">
          <p className="text-xs text-muted">
            Free accounts get 5 validator runs per month.
          </p>
          <button
            type="submit"
            disabled={loading || idea.trim().length < 10}
            className="btn-accent w-full px-6 sm:w-auto"
          >
            {loading ? <Loader2 className="animate-spin" size={15} /> : null}
            {loading ? "Checking collisions..." : "Validate Idea"}
          </button>
        </div>
      </form>

      {error && (
        <div className="card mt-8 border-red-400/30 p-5 text-sm text-red-300">
          {error}
        </div>
      )}

      {matches && matches.length === 0 && (
        <div className="card mt-8 p-8 text-center">
          <p className="font-semibold">No strong collisions found.</p>
          <p className="mt-2 text-sm text-muted">
            Your idea doesn&apos;t closely match any expired patent in the forge
            yet — that can mean uncharted territory. Browse the closest domains
            for adjacent logic.
          </p>
        </div>
      )}

      {primary && (
        <div className="mt-10">
          <p className="text-center text-lg font-semibold">
            Your idea is{" "}
            <span className="text-teal">
              {Math.round(primary.similarity * 100)}% similar
            </span>{" "}
            to an expired patent.
          </p>

          <div className="card mt-5 border-teal/25 p-6 sm:p-7">
            <div className="flex flex-wrap items-center gap-2">
              <DomainBadge domain={primary.domain} />
              {primary.patent_number && (
                <span className="text-xs text-muted">
                  Patent #{primary.patent_number}
                </span>
              )}
            </div>
            <h2 className="mt-3 text-xl font-semibold tracking-tight">
              {primary.title}
            </h2>
            <div className="mt-4">
              <SimilarityBar value={primary.similarity} />
            </div>
            <p className="mt-5 flex items-start gap-2 text-sm leading-relaxed text-ink/90">
              <ShieldCheck size={16} className="mt-0.5 flex-none text-teal" />
              Here is the logic you can legally borrow: {primary.expired_logic}
            </p>
            <Link href={`/blueprint/${primary.id}`} className="btn-accent mt-6">
              View Full Blueprint <ArrowRight size={15} />
            </Link>
          </div>

          {secondary.length > 0 && (
            <div className="mt-8">
              <p className="section-label mb-3">Other overlapping blueprints</p>
              <div className="space-y-3">
                {secondary.map((match) => (
                  <Link
                    key={match.id}
                    href={`/blueprint/${match.id}`}
                    className="card flex items-center justify-between gap-4 p-4 transition hover:border-muted/60"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold">{match.title}</p>
                      <p className="mt-1 line-clamp-1 text-xs text-muted">
                        {match.human_problem}
                      </p>
                    </div>
                    <span className="flex-none rounded-full border border-teal/30 bg-teal-soft px-2.5 py-1 text-xs font-semibold text-teal">
                      {Math.round(match.similarity * 100)}%
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
