import { Gauge } from "lucide-react";
import type { FrameworkAnalysis, FrameworkPillar } from "@/lib/types";
import clsx from "clsx";

function scoreColor(score: number): string {
  if (score >= 70) return "bg-teal";
  if (score >= 45) return "bg-accent";
  return "bg-red-400";
}

const pillars: { key: keyof Pick<FrameworkAnalysis, "market_size" | "competition" | "feasibility" | "monetization" | "uniqueness">; label: string }[] = [
  { key: "market_size", label: "Market Size" },
  { key: "competition", label: "Competition" },
  { key: "feasibility", label: "Feasibility" },
  { key: "monetization", label: "Monetization" },
  { key: "uniqueness", label: "Uniqueness" },
];

function PillarRow({ label, pillar }: { label: string; pillar: FrameworkPillar }) {
  return (
    <div>
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium">{label}</p>
        <span className="text-sm font-bold tabular-nums">{pillar.score}</span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-raised">
        <div
          className={clsx("h-full rounded-full", scoreColor(pillar.score))}
          style={{ width: `${Math.max(3, pillar.score)}%` }}
        />
      </div>
      <p className="mt-1.5 text-xs leading-relaxed text-muted">{pillar.assessment}</p>
    </div>
  );
}

/** The 5-point validation, visible to every visitor on the blueprint page. */
export function ValidationScorecard({
  validation,
}: {
  validation: FrameworkAnalysis;
}) {
  return (
    <section className="card border-teal/25 p-6 sm:p-7">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2.5 text-sm font-semibold uppercase tracking-[0.12em] text-ink">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-soft text-teal">
            <Gauge size={15} />
          </span>
          5-Point Validation
        </h2>
        <span
          className={clsx(
            "flex h-12 w-12 items-center justify-center rounded-full border-[3px] text-base font-bold tabular-nums",
            validation.overall_score >= 70
              ? "border-teal text-teal"
              : validation.overall_score >= 45
                ? "border-accent text-accent"
                : "border-red-400 text-red-300"
          )}
        >
          {validation.overall_score}
        </span>
      </div>
      <div className="mt-5 grid gap-x-8 gap-y-5 sm:grid-cols-2">
        {pillars.map(({ key, label }) => (
          <PillarRow key={key} label={label} pillar={validation[key]} />
        ))}
      </div>
      {validation.verdict && (
        <p className="mt-5 border-t border-edge pt-4 text-sm leading-relaxed text-ink/90">
          {validation.verdict}
        </p>
      )}
      <p className="mt-3 text-xs text-muted">
        AI-scored against the 5-Point Validation Framework using expired-patent
        evidence and real community demand — a structured signal, not a guarantee.
      </p>
    </section>
  );
}
