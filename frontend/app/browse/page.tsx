"use client";

import { Loader2, Lock, SlidersHorizontal } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { BlueprintCard } from "@/components/BlueprintCard";
import { CategoryPills } from "@/components/CategoryPills";
import { SearchBar } from "@/components/SearchBar";
import { getMe, listBlueprints } from "@/lib/api";
import type { BlueprintSummary } from "@/lib/types";
import clsx from "clsx";

const PAGE_SIZE = 20;

function BrowseContent() {
  const router = useRouter();
  const params = useSearchParams();

  const q = params.get("q") ?? "";
  const domain = params.get("domain");
  const sort = params.get("sort") ?? "newest";
  const minBuild = Number(params.get("min_buildability") ?? 0);
  const publicDomainOnly = params.get("public_domain_only") === "1";

  const [items, setItems] = useState<BlueprintSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [paidTier, setPaidTier] = useState(false);
  const [page, setPage] = useState(0);

  const setParam = useCallback(
    (key: string, value: string | null) => {
      const next = new URLSearchParams(params.toString());
      if (value === null || value === "" || value === "0") next.delete(key);
      else next.set(key, value);
      router.replace(`/browse?${next.toString()}`, { scroll: false });
    },
    [params, router]
  );

  useEffect(() => {
    getMe()
      .then((me) => setPaidTier(me.features.prompts_unlocked))
      .catch(() => setPaidTier(false));
  }, []);

  useEffect(() => {
    setPage(0);
  }, [q, domain, sort, minBuild, publicDomainOnly]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    listBlueprints({
      q: q || undefined,
      domain: domain || undefined,
      sort,
      min_buildability: minBuild || undefined,
      public_domain_only: publicDomainOnly || undefined,
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    })
      .then((data) => {
        if (cancelled) return;
        setItems((prev) => (page === 0 ? data.items : [...prev, ...data.items]));
        setTotal(data.total);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message ?? "Failed to load blueprints");
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [q, domain, sort, minBuild, publicDomainOnly, page]);

  const domainLabel =
    domain === "software"
      ? "software problems"
      : domain === "mechanical"
        ? "mechanical upgrades"
        : domain === "medical"
          ? "medical friction points"
          : "problems";

  const filters = (
    <div className="space-y-6">
      <div>
        <p className="section-label mb-3">Buildability Score</p>
        <input
          type="range"
          min={0}
          max={90}
          step={10}
          value={minBuild}
          onChange={(event) => setParam("min_buildability", event.target.value)}
          className="w-full accent-[#F2A93B]"
          aria-label="Minimum buildability score"
        />
        <p className="mt-1.5 text-xs text-muted">
          {minBuild > 0 ? `${minBuild}%+ AI buildability` : "Any score"}
        </p>
      </div>

      <div>
        <p className="section-label mb-3">Filters</p>
        <button
          type="button"
          onClick={() => {
            if (!paidTier) {
              router.push("/pricing");
              return;
            }
            setParam("public_domain_only", publicDomainOnly ? null : "1");
          }}
          className="flex w-full items-center justify-between rounded-lg border border-edge px-3.5 py-2.5 text-sm transition hover:border-muted"
        >
          <span className="flex items-center gap-2">
            Public Domain Only
            {!paidTier && <Lock size={13} className="text-accent" />}
          </span>
          <span
            className={clsx(
              "relative h-5 w-9 rounded-full transition",
              publicDomainOnly ? "bg-accent" : "bg-raised"
            )}
          >
            <span
              className={clsx(
                "absolute top-0.5 h-4 w-4 rounded-full bg-ink transition-all",
                publicDomainOnly ? "left-[18px]" : "left-0.5"
              )}
            />
          </span>
        </button>
        {!paidTier && (
          <p className="mt-1.5 text-xs text-muted">
            Verified-status filter — a paid plan feature.
          </p>
        )}
      </div>

      <div>
        <p className="section-label mb-3">Sort by</p>
        <select
          className="input"
          value={sort}
          onChange={(event) => setParam("sort", event.target.value)}
          aria-label="Sort results"
        >
          <option value="newest">Newest</option>
          <option value="demand">Highest Demand</option>
          <option value="buildability">Highest Buildability</option>
        </select>
      </div>
    </div>
  );

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="mx-auto max-w-2xl space-y-5">
        <SearchBar
          key={q}
          initialQuery={q}
          onSearch={(value) => setParam("q", value || null)}
        />
        <CategoryPills active={domain} onSelect={(value) => setParam("domain", value)} />
      </div>

      <div className="mt-10 lg:grid lg:grid-cols-[240px_1fr] lg:gap-10">
        {/* Mobile filter toggle */}
        <div className="mb-4 lg:hidden">
          <button
            type="button"
            className="btn-ghost w-full"
            onClick={() => setFiltersOpen((v) => !v)}
          >
            <SlidersHorizontal size={15} />
            {filtersOpen ? "Hide filters" : "Show filters"}
          </button>
          {filtersOpen && <div className="card mt-3 p-5">{filters}</div>}
        </div>

        {/* Desktop sidebar */}
        <aside className="hidden lg:block">
          <div className="sticky top-24">{filters}</div>
        </aside>

        <div>
          <p className="text-sm text-muted">
            {loading && page === 0 ? (
              "Searching the forge..."
            ) : (
              <>
                <span className="font-semibold text-ink">{total}</span>{" "}
                {domainLabel} found{q ? ` for “${q}”` : ""}
              </>
            )}
          </p>

          {error && (
            <div className="card mt-4 border-red-400/30 p-5 text-sm text-red-300">
              {error}
            </div>
          )}

          <div className="mt-4 space-y-4">
            {items.map((blueprint) => (
              <BlueprintCard key={blueprint.id} blueprint={blueprint} variant="list" />
            ))}
          </div>

          {loading && (
            <div className="flex justify-center py-10 text-muted">
              <Loader2 className="animate-spin" size={22} />
            </div>
          )}

          {!loading && items.length === 0 && !error && (
            <div className="card mt-4 p-10 text-center text-sm text-muted">
              No blueprints match those filters yet. Try broadening your search.
            </div>
          )}

          {!loading && items.length < total && (
            <div className="mt-6 text-center">
              <button className="btn-ghost" onClick={() => setPage((p) => p + 1)}>
                Load more
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function BrowsePage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-24 text-muted">
          <Loader2 className="animate-spin" size={22} />
        </div>
      }
    >
      <BrowseContent />
    </Suspense>
  );
}
