"use client";

import {
  Bookmark,
  CreditCard,
  KeyRound,
  LayoutDashboard,
  Loader2,
  Plus,
  Trash2,
  type LucideIcon,
} from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect, useState } from "react";
import { BlueprintCard } from "@/components/BlueprintCard";
import {
  createApiKey,
  createCheckout,
  getMe,
  getSaved,
  listApiKeys,
  openPortal,
  revokeApiKey,
  API_URL,
} from "@/lib/api";
import { getSupabase } from "@/lib/supabase/client";
import type { ApiKey, BlueprintSummary, Me } from "@/lib/types";
import clsx from "clsx";

type Tab = "dashboard" | "saved" | "keys" | "billing";

const tabs: { id: Tab; label: string; icon: LucideIcon }[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "saved", label: "Saved Blueprints", icon: Bookmark },
  { id: "keys", label: "API Keys", icon: KeyRound },
  { id: "billing", label: "Billing", icon: CreditCard },
];

function UsageBar({
  label,
  used,
  limit,
}: {
  label: string;
  used: number;
  limit: number;
}) {
  const pct = Math.min(100, Math.round((used / Math.max(1, limit)) * 100));
  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted">{label}</span>
        <span className="font-medium">
          {used.toLocaleString()} / {limit.toLocaleString()}
        </span>
      </div>
      <div className="mt-2 h-2 overflow-hidden rounded-full bg-raised">
        <div
          className={clsx(
            "h-full rounded-full",
            pct >= 90 ? "bg-red-400" : "bg-accent"
          )}
          style={{ width: `${Math.max(2, pct)}%` }}
        />
      </div>
    </div>
  );
}

function daysUntilReset(resetAt: string): number {
  const reset = new Date(resetAt).getTime() + 30 * 24 * 3600 * 1000;
  return Math.max(0, Math.ceil((reset - Date.now()) / (24 * 3600 * 1000)));
}

function AccountContent() {
  const router = useRouter();
  const params = useSearchParams();
  const checkoutSuccess = params.get("checkout") === "success";

  const [tab, setTab] = useState<Tab>("dashboard");
  const [me, setMe] = useState<Me | null>(null);
  const [saved, setSaved] = useState<BlueprintSummary[]>([]);
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checked, setChecked] = useState(false);

  const refresh = useCallback(() => {
    getMe().then(setMe).catch(() => undefined);
    getSaved().then((data) => setSaved(data.items)).catch(() => undefined);
    listApiKeys().then((data) => setKeys(data.items)).catch(() => undefined);
  }, []);

  useEffect(() => {
    getSupabase()
      .auth.getSession()
      .then(({ data }) => {
        if (!data.session) {
          router.replace("/login?next=/account");
        } else {
          setChecked(true);
          refresh();
        }
      })
      .catch(() => router.replace("/login?next=/account"));
  }, [router, refresh]);

  // After Stripe checkout, the webhook may lag a few seconds behind redirect.
  useEffect(() => {
    if (!checkoutSuccess || !checked) return;
    const timer = setInterval(() => {
      getMe().then((data) => {
        setMe(data);
        if (data.tier !== "free") clearInterval(timer);
      }).catch(() => undefined);
    }, 3000);
    const stop = setTimeout(() => clearInterval(timer), 30000);
    return () => {
      clearInterval(timer);
      clearTimeout(stop);
    };
  }, [checkoutSuccess, checked]);

  async function act(name: string, fn: () => Promise<void>) {
    setBusy(name);
    setError(null);
    try {
      await fn();
    } catch (err: any) {
      setError(err?.message ?? "Something went wrong");
    } finally {
      setBusy(null);
    }
  }

  if (!checked || !me) {
    return (
      <div className="flex justify-center py-24 text-muted">
        <Loader2 className="animate-spin" size={22} />
      </div>
    );
  }

  const tierBadge = (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide",
        me.tier === "free"
          ? "border-edge text-muted"
          : "border-accent/40 bg-accent-soft text-accent"
      )}
    >
      {me.tier_name} Plan
    </span>
  );

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-12">
      {checkoutSuccess && (
        <div className="card mb-6 border-teal/40 bg-teal-soft p-4 text-sm text-teal">
          Payment successful — welcome aboard! Your plan activates within a few
          seconds of Stripe confirming the subscription.
        </div>
      )}

      <div className="lg:grid lg:grid-cols-[230px_1fr] lg:gap-10">
        {/* Sidebar (desktop) / tab bar (mobile) */}
        <aside>
          <div className="mb-6 hidden lg:block">
            <p className="text-sm font-semibold">{me.email}</p>
            <div className="mt-2">{tierBadge}</div>
          </div>
          <nav className="mb-6 flex gap-1 overflow-x-auto lg:mb-0 lg:flex-col">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => {
                  setTab(id);
                  setNewKey(null);
                }}
                className={clsx(
                  "flex flex-none items-center gap-2.5 rounded-lg px-3.5 py-2.5 text-sm transition",
                  tab === id
                    ? "bg-surface text-ink"
                    : "text-muted hover:text-ink"
                )}
              >
                <Icon size={16} /> {label}
              </button>
            ))}
          </nav>
        </aside>

        <div>
          <div className="mb-6 flex items-center justify-between lg:hidden">
            <p className="text-sm font-semibold">{me.email}</p>
            {tierBadge}
          </div>

          {error && (
            <div className="card mb-6 border-red-400/30 p-4 text-sm text-red-300">
              {error}
            </div>
          )}

          {tab === "dashboard" && (
            <div className="space-y-6">
              <div className="card p-6">
                <h2 className="font-semibold">Usage this month</h2>
                <div className="mt-5 space-y-5">
                  <UsageBar
                    label="Searches"
                    used={me.usage.searches_used}
                    limit={me.usage.searches_limit}
                  />
                  <UsageBar
                    label="Validator runs"
                    used={me.usage.validations_used}
                    limit={me.usage.validations_limit}
                  />
                </div>
                <p className="mt-4 text-xs text-muted">
                  Resets in {daysUntilReset(me.usage.reset_at)} days.
                </p>
              </div>

              {me.tier === "free" && (
                <div className="card border-accent/40 p-6">
                  <h3 className="font-semibold">Unlock the full forge</h3>
                  <p className="mt-1.5 text-sm text-muted">
                    Master prompts, full build plans, and 10x the searches start
                    at $19/month.
                  </p>
                  <Link href="/pricing" className="btn-accent mt-4">
                    View Plans
                  </Link>
                </div>
              )}

              <div>
                <div className="mb-4 flex items-center justify-between">
                  <h2 className="font-semibold">Saved blueprints</h2>
                  <button
                    onClick={() => setTab("saved")}
                    className="text-sm text-accent"
                  >
                    View all
                  </button>
                </div>
                {saved.length > 0 ? (
                  <div className="grid gap-5 sm:grid-cols-2">
                    {saved.slice(0, 4).map((blueprint) => (
                      <BlueprintCard key={blueprint.id} blueprint={blueprint} />
                    ))}
                  </div>
                ) : (
                  <div className="card p-8 text-center text-sm text-muted">
                    Nothing saved yet —{" "}
                    <Link href="/browse" className="text-accent">
                      browse blueprints
                    </Link>{" "}
                    and bookmark the ones worth building.
                  </div>
                )}
              </div>
            </div>
          )}

          {tab === "saved" && (
            <div>
              <h2 className="mb-4 font-semibold">Saved blueprints</h2>
              {saved.length > 0 ? (
                <div className="grid gap-5 sm:grid-cols-2">
                  {saved.map((blueprint) => (
                    <BlueprintCard key={blueprint.id} blueprint={blueprint} />
                  ))}
                </div>
              ) : (
                <div className="card p-10 text-center text-sm text-muted">
                  No saved blueprints yet.
                </div>
              )}
            </div>
          )}

          {tab === "keys" && (
            <div className="space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <h2 className="font-semibold">Developer API keys</h2>
                {me.features.api_access && (
                  <button
                    className="btn-accent"
                    disabled={busy === "create-key"}
                    onClick={() =>
                      act("create-key", async () => {
                        const { key } = await createApiKey("default");
                        setNewKey(key);
                        const { items } = await listApiKeys();
                        setKeys(items);
                      })
                    }
                  >
                    <Plus size={15} /> New key
                  </button>
                )}
              </div>

              {!me.features.api_access ? (
                <div className="card border-accent/40 p-8 text-center">
                  <p className="font-semibold">API access is a Pro feature</p>
                  <p className="mx-auto mt-2 max-w-md text-sm text-muted">
                    Query blueprints and the validator programmatically with the
                    REST API — $49/month on the Pro plan.
                  </p>
                  <Link href="/pricing" className="btn-accent mt-5">
                    Upgrade to Pro
                  </Link>
                </div>
              ) : (
                <>
                  {newKey && (
                    <div className="card border-teal/40 p-5">
                      <p className="text-sm font-semibold text-teal">
                        Copy your new key now — it won&apos;t be shown again.
                      </p>
                      <code className="mt-3 block overflow-x-auto rounded-lg border border-edge bg-base p-3 font-mono text-xs">
                        {newKey}
                      </code>
                      <p className="mt-3 text-xs text-muted">
                        Use it as an <code>X-API-Key</code> header against{" "}
                        <code>{API_URL}/api/v1/blueprints</code>
                      </p>
                    </div>
                  )}
                  <div className="card divide-y divide-edge">
                    {keys.length === 0 && (
                      <p className="p-6 text-sm text-muted">No API keys yet.</p>
                    )}
                    {keys.map((key) => (
                      <div
                        key={key.id}
                        className="flex items-center justify-between gap-4 p-4"
                      >
                        <div className="min-w-0">
                          <p className="font-mono text-sm">
                            {key.key_prefix}••••••••
                            {key.revoked_at && (
                              <span className="ml-2 text-xs text-red-300">revoked</span>
                            )}
                          </p>
                          <p className="mt-1 text-xs text-muted">
                            Created {new Date(key.created_at).toLocaleDateString()}
                            {key.last_used_at &&
                              ` · last used ${new Date(key.last_used_at).toLocaleDateString()}`}
                          </p>
                        </div>
                        {!key.revoked_at && (
                          <button
                            className="rounded-lg p-2 text-muted transition hover:text-red-300"
                            title="Revoke key"
                            disabled={busy === `revoke-${key.id}`}
                            onClick={() =>
                              act(`revoke-${key.id}`, async () => {
                                await revokeApiKey(key.id);
                                const { items } = await listApiKeys();
                                setKeys(items);
                              })
                            }
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {tab === "billing" && (
            <div className="space-y-6">
              <div className="card p-6">
                <h2 className="font-semibold">Current plan</h2>
                <div className="mt-3 flex items-center gap-3">
                  {tierBadge}
                  <span className="text-sm text-muted">
                    {me.tier === "free"
                      ? "$0/month"
                      : me.tier === "builder"
                        ? "$19/month"
                        : "$49/month"}
                  </span>
                </div>
                <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                  {me.has_billing && (
                    <button
                      className="btn-ghost"
                      disabled={busy === "portal"}
                      onClick={() =>
                        act("portal", async () => {
                          const { url } = await openPortal();
                          window.location.href = url;
                        })
                      }
                    >
                      {busy === "portal" && (
                        <Loader2 className="animate-spin" size={15} />
                      )}
                      Manage billing & invoices
                    </button>
                  )}
                  {me.tier !== "pro" && (
                    <button
                      className="btn-accent"
                      disabled={busy === "upgrade"}
                      onClick={() =>
                        act("upgrade", async () => {
                          const plan = me.tier === "free" ? "builder" : "pro";
                          const { url } = await createCheckout(plan);
                          window.location.href = url;
                        })
                      }
                    >
                      {busy === "upgrade" && (
                        <Loader2 className="animate-spin" size={15} />
                      )}
                      {me.tier === "free" ? "Upgrade — from $19/mo" : "Upgrade to Pro — $49/mo"}
                    </button>
                  )}
                </div>
                <p className="mt-4 text-xs text-muted">
                  Subscriptions are handled securely by Stripe. Cancel anytime
                  from the billing portal.
                </p>
              </div>

              {me.features.export && (
                <div className="card p-6">
                  <h2 className="font-semibold">Bulk export</h2>
                  <p className="mt-1.5 text-sm text-muted">
                    Download every public blueprint as CSV (Pro).
                  </p>
                  <button
                    className="btn-ghost mt-4"
                    disabled={busy === "export"}
                    onClick={() =>
                      act("export", async () => {
                        const { getAccessToken } = await import("@/lib/supabase/client");
                        const token = await getAccessToken();
                        const response = await fetch(
                          `${API_URL}/api/v1/blueprints/export`,
                          { headers: token ? { Authorization: `Bearer ${token}` } : {} }
                        );
                        if (!response.ok) throw new Error("Export failed");
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        const link = document.createElement("a");
                        link.href = url;
                        link.download = "problemforge-blueprints.csv";
                        link.click();
                        URL.revokeObjectURL(url);
                      })
                    }
                  >
                    {busy === "export" && <Loader2 className="animate-spin" size={15} />}
                    Download CSV
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AccountPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-24 text-muted">
          <Loader2 className="animate-spin" size={22} />
        </div>
      }
    >
      <AccountContent />
    </Suspense>
  );
}
