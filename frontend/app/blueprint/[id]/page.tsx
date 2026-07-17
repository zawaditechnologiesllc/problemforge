"use client";

import {
  Bookmark,
  BookmarkCheck,
  Hammer,
  Loader2,
  MessageSquareWarning,
  Terminal,
  Unlock,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import {
  BuildabilityBadge,
  DemandBadge,
  DomainBadge,
  PublicDomainBadge,
} from "@/components/Badges";
import { CopyButton } from "@/components/CopyButton";
import { LockedPanel } from "@/components/LockedPanel";
import {
  getBlueprint,
  getRelated,
  logPromptCopy,
  saveBlueprint,
  unsaveBlueprint,
} from "@/lib/api";
import { getSupabase } from "@/lib/supabase/client";
import type { BlueprintDetail, BlueprintSummary } from "@/lib/types";

function SectionCard({
  icon: Icon,
  title,
  children,
  action,
}: {
  icon: LucideIcon;
  title: string;
  children: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <section className="card p-6 sm:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2.5 text-sm font-semibold uppercase tracking-[0.12em] text-ink">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Icon size={15} />
          </span>
          {title}
        </h2>
        {action}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}

function BuildPlan({ text }: { text: string }) {
  const lines = text.split("\n").filter((line) => line.trim());
  return (
    <ol className="space-y-4">
      {lines.map((line, index) => {
        const cleaned = line.replace(/^\s*\d+[.)]\s*/, "");
        return (
          <li key={index} className="flex gap-3.5">
            <span className="mt-0.5 flex h-6 w-6 flex-none items-center justify-center rounded-full border border-teal/40 bg-teal-soft text-xs font-semibold text-teal">
              {index + 1}
            </span>
            <p className="text-sm leading-relaxed text-ink/90">{cleaned}</p>
          </li>
        );
      })}
    </ol>
  );
}

export default function BlueprintPage() {
  const { id } = useParams<{ id: string }>();
  const [blueprint, setBlueprint] = useState<BlueprintDetail | null>(null);
  const [related, setRelated] = useState<BlueprintSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!id) return;
    getBlueprint(id)
      .then(setBlueprint)
      .catch((err) => setError(err.message ?? "Failed to load blueprint"));
    getRelated(id)
      .then((data) => setRelated(data.items))
      .catch(() => setRelated([]));
    getSupabase()
      .auth.getSession()
      .then(({ data }) => setSignedIn(!!data.session))
      .catch(() => setSignedIn(false));
  }, [id]);

  async function toggleSave() {
    if (!blueprint || saving) return;
    setSaving(true);
    try {
      if (blueprint.saved) {
        await unsaveBlueprint(blueprint.id);
        setBlueprint({ ...blueprint, saved: false });
      } else {
        await saveBlueprint(blueprint.id);
        setBlueprint({ ...blueprint, saved: true });
      }
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  }

  if (error) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-24 text-center">
        <p className="text-lg font-semibold">Blueprint not found</p>
        <p className="mt-2 text-sm text-muted">{error}</p>
        <Link href="/browse" className="btn-accent mt-6">
          Back to Browse
        </Link>
      </div>
    );
  }

  if (!blueprint) {
    return (
      <div className="flex justify-center py-24 text-muted">
        <Loader2 className="animate-spin" size={22} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      {/* Header */}
      <div className="max-w-3xl">
        <div className="flex flex-wrap items-center gap-2">
          <DomainBadge domain={blueprint.domain} />
          <DemandBadge score={blueprint.demand_signal_score} />
          <BuildabilityBadge score={blueprint.buildability_score} />
          <PublicDomainBadge />
        </div>
        <h1 className="mt-4 text-3xl font-bold leading-tight tracking-tight sm:text-4xl">
          {blueprint.title}
        </h1>
        <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-muted">
          {blueprint.patent_number && (
            <span>Derived from Patent #{blueprint.patent_number}</span>
          )}
          {blueprint.patent?.filing_date && (
            <span>Filed {blueprint.patent.filing_date}</span>
          )}
          {signedIn && (
            <button
              onClick={toggleSave}
              disabled={saving}
              className="inline-flex items-center gap-1.5 text-accent transition hover:text-accent-hover"
            >
              {blueprint.saved ? <BookmarkCheck size={15} /> : <Bookmark size={15} />}
              {blueprint.saved ? "Saved" : "Save"}
            </button>
          )}
        </div>
        {blueprint.patent?.legal_status && (
          <p className="mt-2 text-xs text-muted/80">
            Status: {blueprint.patent.legal_status}
          </p>
        )}
      </div>

      <div className="mt-10 gap-10 lg:grid lg:grid-cols-[1fr_290px]">
        {/* Four-section blueprint */}
        <div className="space-y-6">
          <SectionCard icon={MessageSquareWarning} title="The Human Problem">
            <p className="text-[15px] leading-relaxed text-ink/90">
              {blueprint.human_problem}
            </p>
          </SectionCard>

          <SectionCard icon={Unlock} title="The Expired Logic">
            <p className="text-[15px] leading-relaxed text-ink/90">
              {blueprint.expired_logic}
            </p>
          </SectionCard>

          <SectionCard icon={Hammer} title="How a Vibe Coder Builds It Today">
            {blueprint.locked || !blueprint.build_plan ? (
              <LockedPanel message="Upgrade to the Builder plan to unlock the full 3-step build plan." />
            ) : (
              <BuildPlan text={blueprint.build_plan} />
            )}
          </SectionCard>

          <SectionCard
            icon={Terminal}
            title="Prompt for Cursor / Windsurf"
            action={
              !blueprint.locked && blueprint.master_prompt ? (
                <CopyButton
                  text={blueprint.master_prompt}
                  onCopied={() => logPromptCopy(blueprint.id).catch(() => undefined)}
                />
              ) : undefined
            }
          >
            {blueprint.locked || !blueprint.master_prompt ? (
              <LockedPanel message="Upgrade to unlock the ready-to-paste master prompt and start building this MVP now." />
            ) : (
              <pre className="max-h-[480px] overflow-auto whitespace-pre-wrap rounded-lg border border-edge bg-base p-5 font-mono text-[13px] leading-relaxed text-ink/90">
                {blueprint.master_prompt}
              </pre>
            )}
          </SectionCard>
        </div>

        {/* Related sidebar */}
        <aside className="mt-10 lg:mt-0">
          <p className="section-label mb-4">Related Blueprints</p>
          <div className="space-y-3">
            {related.map((item) => (
              <Link
                key={item.id}
                href={`/blueprint/${item.id}`}
                className="card block p-4 transition hover:border-muted/60"
              >
                <p className="text-sm font-semibold leading-snug">{item.title}</p>
                <p className="mt-1.5 line-clamp-2 text-xs leading-relaxed text-muted">
                  {item.human_problem}
                </p>
                <div className="mt-2.5">
                  <BuildabilityBadge score={item.buildability_score} />
                </div>
              </Link>
            ))}
            {related.length === 0 && (
              <p className="text-sm text-muted">No related blueprints yet.</p>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
