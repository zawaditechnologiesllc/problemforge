import Link from "next/link";
import { ArrowRight, Terminal } from "lucide-react";
import type { BlueprintSummary } from "@/lib/types";
import {
  BuildabilityBadge,
  DemandBadge,
  DomainBadge,
  PublicDomainBadge,
  ValidationBadge,
} from "@/components/Badges";

export function BlueprintCard({
  blueprint,
  variant = "grid",
}: {
  blueprint: BlueprintSummary;
  variant?: "grid" | "list";
}) {
  if (variant === "list") {
    return (
      <Link
        href={`/blueprint/${blueprint.id}`}
        className="card group block p-5 transition hover:border-muted/60"
      >
        <div className="flex flex-wrap items-center gap-2">
          <DomainBadge domain={blueprint.domain} />
          <PublicDomainBadge />
          <DemandBadge score={blueprint.demand_signal_score} />
          <BuildabilityBadge score={blueprint.buildability_score} />
          <ValidationBadge score={blueprint.validation_score} />
        </div>
        <h3 className="mt-3 text-lg font-semibold tracking-tight group-hover:text-accent">
          {blueprint.title}
        </h3>
        <p className="mt-2 line-clamp-2 text-sm leading-relaxed text-muted">
          {blueprint.human_problem}
        </p>
        <span className="mt-4 inline-flex items-center gap-1.5 text-sm font-medium text-accent">
          View Blueprint <ArrowRight size={15} />
        </span>
      </Link>
    );
  }

  return (
    <div className="card flex flex-col p-6 transition hover:border-muted/60">
      <div className="flex flex-wrap items-center gap-2">
        <PublicDomainBadge />
        <DemandBadge score={blueprint.demand_signal_score} />
        <BuildabilityBadge score={blueprint.buildability_score} />
        <ValidationBadge score={blueprint.validation_score} />
      </div>
      <h3 className="mt-4 text-lg font-semibold leading-snug tracking-tight">
        <Link
          href={`/blueprint/${blueprint.id}`}
          className="transition hover:text-accent"
        >
          {blueprint.title}
        </Link>
      </h3>

      <div className="mt-4">
        <p className="section-label">The Human Problem</p>
        <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-muted">
          {blueprint.human_problem}
        </p>
      </div>

      {blueprint.expired_logic && (
        <div className="mt-4">
          <p className="section-label">The Expired Logic</p>
          <p className="mt-1.5 line-clamp-2 text-sm leading-relaxed text-muted">
            {blueprint.expired_logic}
          </p>
        </div>
      )}

      <div className="mt-6 flex-1" />
      <Link href={`/blueprint/${blueprint.id}`} className="btn-accent w-full">
        <Terminal size={15} /> Copy Master Prompt for Cursor
      </Link>
    </div>
  );
}
