import {
  Fingerprint,
  MessageCircleQuestion,
  Swords,
  Target,
  Users,
  Wallet,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import type {
  CommunityMatch,
  CommunityQuestion,
  FrameworkAnalysis,
  FrameworkPillar,
} from "@/lib/types";
import clsx from "clsx";

function scoreColor(score: number): string {
  if (score >= 70) return "bg-teal";
  if (score >= 45) return "bg-accent";
  return "bg-red-400";
}

function PillarCard({
  icon: Icon,
  title,
  subtitle,
  pillar,
  highlightLabel,
  highlight,
}: {
  icon: LucideIcon;
  title: string;
  subtitle: string;
  pillar: FrameworkPillar;
  highlightLabel: string;
  highlight: React.ReactNode;
}) {
  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent-soft text-accent">
            <Icon size={15} />
          </span>
          <div>
            <p className="text-sm font-semibold">{title}</p>
            <p className="text-[11px] text-muted">{subtitle}</p>
          </div>
        </div>
        <span className="text-lg font-bold tabular-nums">{pillar.score}</span>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-raised">
        <div
          className={clsx("h-full rounded-full", scoreColor(pillar.score))}
          style={{ width: `${Math.max(3, pillar.score)}%` }}
        />
      </div>
      <p className="mt-3 text-sm leading-relaxed text-muted">{pillar.assessment}</p>
      {highlight && (
        <div className="mt-3 rounded-lg border border-teal/25 bg-teal-soft p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-teal">
            {highlightLabel}
          </p>
          <div className="mt-1 text-sm leading-relaxed text-ink/90">{highlight}</div>
        </div>
      )}
    </div>
  );
}

export function FrameworkReport({ framework }: { framework: FrameworkAnalysis }) {
  return (
    <div className="mt-12">
      <h2 className="text-xl font-semibold tracking-tight">
        5-Point Validation Framework
      </h2>
      <p className="mt-1 text-sm text-muted">
        Your concept, pressure-tested against the five pillars that decide
        whether an app is worth building.
      </p>

      {/* Overall verdict */}
      <div className="card mt-5 flex flex-col gap-5 p-6 sm:flex-row sm:items-center">
        <div className="flex flex-none flex-col items-center">
          <span
            className={clsx(
              "flex h-20 w-20 items-center justify-center rounded-full border-4 text-2xl font-bold tabular-nums",
              framework.overall_score >= 70
                ? "border-teal text-teal"
                : framework.overall_score >= 45
                  ? "border-accent text-accent"
                  : "border-red-400 text-red-300"
            )}
          >
            {framework.overall_score}
          </span>
          <span className="mt-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted">
            Overall
          </span>
        </div>
        <p className="text-[15px] leading-relaxed text-ink/90">{framework.verdict}</p>
      </div>

      {/* The five pillars */}
      <div className="mt-5 grid gap-4 md:grid-cols-2">
        <PillarCard
          icon={Users}
          title="1. Market Size"
          subtitle="Are enough people discussing this problem?"
          pillar={framework.market_size}
          highlightLabel="Best demographic to target"
          highlight={framework.market_size.best_demographic}
        />
        <PillarCard
          icon={Swords}
          title="2. Competition"
          subtitle="Do existing solutions have proven demand?"
          pillar={framework.competition}
          highlightLabel="Gaps to differentiate on"
          highlight={
            framework.competition.gaps && framework.competition.gaps.length > 0 ? (
              <ul className="list-disc space-y-1 pl-4">
                {framework.competition.gaps.map((gap) => (
                  <li key={gap}>{gap}</li>
                ))}
              </ul>
            ) : null
          }
        />
        <PillarCard
          icon={Wrench}
          title="3. Feasibility"
          subtitle="MVP in 2–3 months with no-code or a small team?"
          pillar={framework.feasibility}
          highlightLabel="Smallest shippable MVP"
          highlight={framework.feasibility.mvp_scope}
        />
        <PillarCard
          icon={Wallet}
          title="4. Monetization Potential"
          subtitle="Is there a concrete revenue model?"
          pillar={framework.monetization}
          highlightLabel="Recommended model"
          highlight={framework.monetization.recommended_model}
        />
        <PillarCard
          icon={Fingerprint}
          title="5. Uniqueness"
          subtitle="Better UX or a focused niche is enough."
          pillar={framework.uniqueness}
          highlightLabel="Sharpest angle"
          highlight={framework.uniqueness.angle}
        />
        <div className="card flex items-center justify-center p-5 text-center">
          <div>
            <Target className="mx-auto text-muted" size={22} />
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Scores are AI assessments grounded in expired-patent matches and
              real community questions — a structured starting point, not a
              guarantee.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export function CommunityMatches({ matches }: { matches: CommunityMatch[] }) {
  if (matches.length === 0) return null;
  return (
    <div className="mt-12">
      <h2 className="text-xl font-semibold tracking-tight">
        Startup communities are asking for this
      </h2>
      <p className="mt-1 text-sm text-muted">
        Public posts from idea communities (r/SomebodyMakeThis, r/startups,
        and friends) that closely match your concept — live demand, with
        receipts.
      </p>
      <div className="card mt-4 divide-y divide-edge">
        {matches.map((match) => (
          <a
            key={match.url}
            href={match.url}
            target="_blank"
            rel="noopener nofollow"
            className="flex items-center justify-between gap-4 p-4 transition hover:bg-raised/50"
          >
            <div className="min-w-0">
              <p className="truncate text-sm text-ink/90">{match.title}</p>
              <p className="mt-1 text-xs text-muted">
                {match.community ?? "reddit"} · {match.upvotes} upvotes ·{" "}
                {match.num_comments} comments
              </p>
            </div>
            <span className="flex-none rounded-full border border-teal/30 bg-teal-soft px-2.5 py-1 text-xs font-semibold text-teal">
              {Math.round(match.similarity * 100)}%
            </span>
          </a>
        ))}
      </div>
    </div>
  );
}

export function CommunityQuestions({
  questions,
}: {
  questions: CommunityQuestion[];
}) {
  if (questions.length === 0) return null;
  return (
    <div className="mt-12">
      <h2 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
        <MessageCircleQuestion size={20} className="text-teal" />
        Real questions from real people
      </h2>
      <p className="mt-1 text-sm text-muted">
        Live gaps pulled from public Reddit and Quora discussions related to
        your idea — the demand you&apos;d be answering.
      </p>
      <div className="card mt-4 divide-y divide-edge">
        {questions.map((question) => (
          <a
            key={question.url}
            href={question.url}
            target="_blank"
            rel="noopener nofollow"
            className="flex items-center justify-between gap-4 p-4 transition hover:bg-raised/50"
          >
            <div className="min-w-0">
              <p className="truncate text-sm text-ink/90">{question.title}</p>
              <p className="mt-1 text-xs text-muted">
                {question.source === "reddit" ? "Reddit" : "Quora"}
                {question.community ? ` · ${question.community}` : ""}
              </p>
            </div>
            {question.engagement != null && question.engagement > 0 && (
              <span className="flex-none rounded-full border border-edge px-2.5 py-1 text-xs text-muted">
                {question.engagement} comments
              </span>
            )}
          </a>
        ))}
      </div>
    </div>
  );
}
