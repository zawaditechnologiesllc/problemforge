import { ShieldCheck, TrendingUp, Zap } from "lucide-react";
import clsx from "clsx";

export function PublicDomainBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-teal/30 bg-teal-soft px-2.5 py-1 text-[11px] font-medium text-teal">
      <ShieldCheck size={12} /> Public Domain
    </span>
  );
}

export function DemandBadge({ score }: { score: number | null }) {
  if (!score || score < 70) return null;
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-teal/30 bg-teal-soft px-2.5 py-1 text-[11px] font-medium text-teal">
      <TrendingUp size={12} /> High Demand
    </span>
  );
}

export function BuildabilityBadge({ score }: { score: number | null }) {
  if (score == null) return null;
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-accent/30 bg-accent-soft px-2.5 py-1 text-[11px] font-medium text-accent">
      <Zap size={12} /> {score}% AI Buildability
    </span>
  );
}

const domainStyles: Record<string, string> = {
  software: "text-sky-300 border-sky-300/30 bg-sky-300/10",
  mechanical: "text-orange-300 border-orange-300/30 bg-orange-300/10",
  medical: "text-emerald-300 border-emerald-300/30 bg-emerald-300/10",
};

const domainLabels: Record<string, string> = {
  software: "Software",
  mechanical: "Mechanical",
  medical: "Medical",
};

export function DomainBadge({ domain }: { domain: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-medium",
        domainStyles[domain] ?? "text-muted border-edge bg-surface"
      )}
    >
      {domainLabels[domain] ?? domain}
    </span>
  );
}
