import {
  Code2,
  FlaskConical,
  Megaphone,
  Palette,
  Plug,
  Settings,
  Sparkles,
  type LucideIcon,
} from "lucide-react";
import type { Playbook } from "@/lib/types";
import clsx from "clsx";

const stages: { key: keyof Playbook["stack"]; label: string; icon: LucideIcon }[] = [
  { key: "design", label: "Design", icon: Palette },
  { key: "coding", label: "Coding", icon: Code2 },
  { key: "configuration", label: "Configuration", icon: Settings },
  { key: "integration", label: "Integration", icon: Plug },
  { key: "testing", label: "Testing", icon: FlaskConical },
];

export function PlaybookSection({ playbook }: { playbook: Playbook }) {
  return (
    <div className="space-y-6">
      {/* Does the problem still exist? */}
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <p className="section-label">Does this problem still exist?</p>
          <span
            className={clsx(
              "rounded-full border px-2.5 py-1 text-[11px] font-semibold",
              playbook.problem_today.still_exists
                ? "border-teal/40 bg-teal-soft text-teal"
                : "border-edge text-muted"
            )}
          >
            {playbook.problem_today.still_exists ? "Yes — still real today" : "Uncertain"}
          </span>
        </div>
        <p className="mt-2 text-sm leading-relaxed text-ink/90">
          {playbook.problem_today.assessment}
        </p>
        {playbook.problem_today.evidence && (
          <p className="mt-1.5 text-xs text-muted">
            Evidence: {playbook.problem_today.evidence}
          </p>
        )}
      </div>

      {/* How to solve it now with AI */}
      <div className="rounded-lg border border-accent/25 bg-accent-soft p-4">
        <p className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-accent">
          <Sparkles size={13} /> How to solve it now with AI
        </p>
        <p className="mt-2 text-sm leading-relaxed text-ink/90">
          {playbook.ai_solution}
        </p>
      </div>

      {/* The stack, end to end */}
      <div>
        <p className="section-label mb-3">The stack, end to end</p>
        <div className="space-y-3">
          {stages.map(({ key, label, icon: Icon }) => (
            <div key={key} className="flex gap-3.5 rounded-lg border border-edge p-3.5">
              <span className="mt-0.5 flex h-7 w-7 flex-none items-center justify-center rounded-lg bg-teal-soft text-teal">
                <Icon size={14} />
              </span>
              <div className="min-w-0">
                <p className="text-sm font-semibold">{label}</p>
                <p className="mt-0.5 text-sm leading-relaxed text-muted">
                  {playbook.stack[key]}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Marketing & distribution */}
      <div>
        <p className="section-label mb-3 flex items-center gap-2">
          <Megaphone size={13} /> Marketing & distribution channels
        </p>
        <div className="space-y-3">
          {playbook.marketing.channels.map((channel, index) => (
            <div key={index} className="rounded-lg border border-edge p-3.5">
              <div className="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
                <p className="text-sm font-semibold">{channel.channel}</p>
                {channel.audience && (
                  <p className="text-xs text-teal">reaches: {channel.audience}</p>
                )}
              </div>
              {channel.how && (
                <p className="mt-1 text-sm leading-relaxed text-muted">{channel.how}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
