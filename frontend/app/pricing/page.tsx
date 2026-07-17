"use client";

import { Check, FileText, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createCheckout } from "@/lib/api";
import { getSupabase } from "@/lib/supabase/client";
import clsx from "clsx";

const plans = [
  {
    id: "free",
    name: "Free",
    price: 0,
    tagline: "Start exploring the forge.",
    features: [
      "50 searches per month",
      "Browse all Idea Blueprints",
      "Human Problem + Expired Logic sections",
      "5 validator runs per month",
    ],
    cta: "Get Started",
  },
  {
    id: "builder",
    name: "Builder",
    price: 19,
    tagline: "For makers shipping their next MVP.",
    features: [
      "500 searches per month",
      "Full build plans + master prompts unlocked",
      "Copy prompts straight into Cursor / Windsurf",
      "Public Domain Only verified filter",
      "100 validator runs per month",
      "Save unlimited blueprints",
    ],
    cta: "Start Builder Plan",
    featured: true,
  },
  {
    id: "pro",
    name: "Pro",
    price: 49,
    tagline: "For power users building on the API.",
    features: [
      "2,500 searches per month",
      "Everything in Builder",
      "Developer REST API + API keys",
      "5,000 API requests per month",
      "500 validator runs per month",
    ],
    cta: "Go Pro",
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: 150,
    tagline: "For teams and data products.",
    features: [
      "Everything in Pro",
      "Unlimited API calls",
      "Unlimited searches & validator runs",
      "Bulk data export (CSV)",
      "Priority support",
    ],
    cta: "Start Enterprise Plan",
  },
] as const;

const faqs = [
  {
    q: "What counts as a search?",
    a: "A search is any query you run against the blueprint library — typing in the search bar or hitting the API with a query. Browsing, opening blueprints, and filtering without a query are free and unlimited.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. Subscriptions are managed through Stripe — cancel from your account's billing portal in two clicks and you keep access until the end of the billing period.",
  },
  {
    q: "Are these patents really free to use?",
    a: "Every blueprint comes from a patent that is at least 20 years past filing or officially lapsed for non-payment of maintenance fees, enforced by a hard database-level gate. We show the source status on every blueprint. Still, ProblemForge is informational — not legal advice.",
  },
  {
    q: "What is a master prompt?",
    a: "A ready-to-paste build brief for AI coding tools like Cursor and Windsurf: the product spec, data model, and feature list to scaffold a modern MVP of the expired invention in one shot.",
  },
];

export default function PricingPage() {
  const router = useRouter();
  const [busyPlan, setBusyPlan] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function choosePlan(planId: string) {
    if (planId === "free") {
      router.push("/signup");
      return;
    }
    setError(null);
    setBusyPlan(planId);
    try {
      const { data } = await getSupabase().auth.getSession();
      if (!data.session) {
        router.push(`/login?next=/pricing`);
        return;
      }
      const { url } = await createCheckout(
        planId as "builder" | "pro" | "enterprise"
      );
      window.location.href = url;
    } catch (err: any) {
      setError(err?.message ?? "Could not start checkout. Try again.");
    } finally {
      setBusyPlan(null);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-12 sm:px-6 sm:py-16">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
          Simple pricing for serious builders
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-sm text-muted sm:text-base">
          Browse free forever. Upgrade when you&apos;re ready to copy master
          prompts and ship.
        </p>
      </div>

      {error && (
        <div className="card mx-auto mt-8 max-w-lg border-red-400/30 p-4 text-center text-sm text-red-300">
          {error}
        </div>
      )}

      <div className="mt-12 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        {plans.map((plan) => (
          <div
            key={plan.id}
            className={clsx(
              "card relative flex flex-col p-7",
              "featured" in plan && plan.featured && "border-accent/60 shadow-[0_0_40px_rgba(242,169,59,0.08)]"
            )}
          >
            {"featured" in plan && plan.featured && (
              <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-accent px-3 py-1 text-[11px] font-bold uppercase tracking-wide text-base">
                Most Popular
              </span>
            )}
            <h2 className="text-lg font-semibold">{plan.name}</h2>
            <p className="mt-1 text-sm text-muted">{plan.tagline}</p>
            <p className="mt-5">
              <span className="text-4xl font-bold tracking-tight">
                ${plan.price}
              </span>
              <span className="text-sm text-muted">/month</span>
            </p>
            <ul className="mt-6 space-y-3">
              {plan.features.map((feature) => (
                <li key={feature} className="flex items-start gap-2.5 text-sm">
                  <Check size={16} className="mt-0.5 flex-none text-teal" />
                  <span className="text-ink/90">{feature}</span>
                </li>
              ))}
            </ul>
            <div className="mt-8 flex-1" />
            <button
              onClick={() => choosePlan(plan.id)}
              disabled={busyPlan !== null}
              className={clsx(
                "featured" in plan && plan.featured ? "btn-accent" : "btn-ghost",
                "w-full"
              )}
            >
              {busyPlan === plan.id && <Loader2 className="animate-spin" size={15} />}
              {plan.cta}
            </button>
          </div>
        ))}
      </div>

      {/* Freedom to Operate callout */}
      <div className="card mt-12 flex flex-col items-start gap-5 p-7 sm:flex-row sm:items-center">
        <span className="flex h-11 w-11 flex-none items-center justify-center rounded-lg bg-teal-soft text-teal">
          <FileText size={20} />
        </span>
        <div className="flex-1">
          <h3 className="font-semibold">
            Freedom-to-Operate Report — $99 one-time
          </h3>
          <p className="mt-1 text-sm leading-relaxed text-muted">
            A PDF report re-verifying a patent&apos;s expired status before you
            build on it: statutory-term math, recorded legal status, and a live
            USPTO re-check. An AI-generated informational summary, not legal
            advice. Order from any blueprint page or your account dashboard.
          </p>
        </div>
        <Link href="/account" className="btn-ghost flex-none">
          Order a Report
        </Link>
      </div>

      {/* FAQ */}
      <div className="mx-auto mt-16 max-w-2xl">
        <h2 className="text-center text-xl font-semibold tracking-tight">
          Frequently asked questions
        </h2>
        <div className="mt-6 space-y-3">
          {faqs.map((faq) => (
            <details key={faq.q} className="card group p-5 open:border-muted/50">
              <summary className="cursor-pointer list-none text-sm font-semibold marker:hidden">
                {faq.q}
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-muted">{faq.a}</p>
            </details>
          ))}
        </div>
      </div>
    </div>
  );
}
