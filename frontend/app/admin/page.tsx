"use client";

import {
  Database,
  FileText,
  LayoutDashboard,
  Loader2,
  MessageCircle,
  PanelBottom,
  Play,
  Send,
  Trash2,
  Users as UsersIcon,
  type LucideIcon,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  adminBlueprints,
  adminDeleteBlueprint,
  adminFtoReports,
  adminIngestionRuns,
  adminOverview,
  adminRunTask,
  adminSaveFooter,
  adminSupportReply,
  adminSupportSetStatus,
  adminSupportThread,
  adminSupportThreads,
  adminUpdateBlueprint,
  adminUpdateUser,
  adminUsers,
  fetchSiteSettings,
  getMe,
} from "@/lib/api";
import type {
  AdminBlueprint,
  AdminOverview,
  AdminSupportThread,
  AdminUser,
  FooterSettingsData,
  FtoReport,
  SupportMessage,
} from "@/lib/types";
import clsx from "clsx";

type Tab =
  | "overview"
  | "messages"
  | "blueprints"
  | "users"
  | "fto"
  | "ops"
  | "footer";

const tabs: { id: Tab; label: string; icon: LucideIcon }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "messages", label: "Messages", icon: MessageCircle },
  { id: "blueprints", label: "Blueprints", icon: Database },
  { id: "users", label: "Users", icon: UsersIcon },
  { id: "fto", label: "FTO Reports", icon: FileText },
  { id: "ops", label: "Operations", icon: Play },
  { id: "footer", label: "Site Footer", icon: PanelBottom },
];

const OPS_TASKS = [
  { name: "ingest", label: "Run patent ingestion", detail: "Weekly-style pass across all configured regions" },
  { name: "enrich_blueprints", label: "Enrich blueprints", detail: "Generate playbooks + validation scores (batch of 20)" },
  { name: "backfill_embeddings", label: "Backfill embeddings", detail: "Embed blueprints missing vectors" },
  { name: "ingest_community", label: "Refresh community corpus", detail: "Top posts from startup communities" },
  { name: "ingest_active", label: "Refresh active landscape", detail: "Internal validator caution corpus" },
];

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card p-5">
      <p className="text-2xl font-bold tabular-nums">{value}</p>
      <p className="mt-1 text-xs text-muted">{label}</p>
    </div>
  );
}

export default function AdminPage() {
  const router = useRouter();
  const [authorized, setAuthorized] = useState<boolean | null>(null);
  const [tab, setTab] = useState<Tab>("overview");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [blueprints, setBlueprints] = useState<AdminBlueprint[]>([]);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [fto, setFto] = useState<(FtoReport & { user_id: string })[]>([]);
  const [runs, setRuns] = useState<Record<string, unknown>[]>([]);
  const [footer, setFooter] = useState<FooterSettingsData | null>(null);
  const [query, setQuery] = useState("");
  const [threads, setThreads] = useState<AdminSupportThread[]>([]);
  const [threadFilter, setThreadFilter] = useState<"open" | "closed" | "all">("open");
  const [activeThread, setActiveThread] = useState<AdminSupportThread | null>(null);
  const [threadMessages, setThreadMessages] = useState<SupportMessage[]>([]);
  const [reply, setReply] = useState("");

  useEffect(() => {
    getMe()
      .then((me) => {
        if (!me.is_admin) router.replace("/account");
        else setAuthorized(true);
      })
      .catch(() => router.replace("/login?next=/admin"));
  }, [router]);

  const load = useCallback(
    (which: Tab, q = "") => {
      setError(null);
      const fail = (err: any) => setError(err?.message ?? "Request failed");
      if (which === "overview") adminOverview().then(setOverview).catch(fail);
      if (which === "blueprints")
        adminBlueprints(q || undefined).then((d) => setBlueprints(d.items)).catch(fail);
      if (which === "users")
        adminUsers(q || undefined).then((d) => setUsers(d.items)).catch(fail);
      if (which === "fto") adminFtoReports().then((d) => setFto(d.items)).catch(fail);
      if (which === "ops")
        adminIngestionRuns().then((d) => setRuns(d.items)).catch(fail);
      if (which === "footer")
        fetchSiteSettings().then((d) => setFooter(d.footer)).catch(fail);
      if (which === "messages")
        adminSupportThreads(threadFilter).then((d) => setThreads(d.items)).catch(fail);
    },
    [threadFilter]
  );

  async function openThread(thread: AdminSupportThread) {
    setActiveThread(thread);
    try {
      const data = await adminSupportThread(thread.id);
      setThreadMessages(data.messages);
      setThreads((current) =>
        current.map((t) => (t.id === thread.id ? { ...t, unread: 0 } : t))
      );
    } catch (err: any) {
      setError(err?.message ?? "Could not load thread");
    }
  }

  useEffect(() => {
    if (authorized) load(tab);
  }, [authorized, tab, load]);

  async function act(name: string, fn: () => Promise<void>, success?: string) {
    setBusy(name);
    setError(null);
    setNotice(null);
    try {
      await fn();
      if (success) setNotice(success);
    } catch (err: any) {
      setError(err?.message ?? "Action failed");
    } finally {
      setBusy(null);
    }
  }

  if (authorized === null) {
    return (
      <div className="flex justify-center py-24 text-muted">
        <Loader2 className="animate-spin" size={22} />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Admin</h1>
          <p className="text-sm text-muted">Operate ProblemForge — a Zawadi Technologies LLC product.</p>
        </div>
      </div>

      <nav className="mb-6 flex gap-1 overflow-x-auto border-b border-edge pb-px">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              "flex flex-none items-center gap-2 border-b-2 px-3.5 py-2.5 text-sm transition",
              tab === id
                ? "border-accent text-ink"
                : "border-transparent text-muted hover:text-ink"
            )}
          >
            <Icon size={15} /> {label}
          </button>
        ))}
      </nav>

      {error && (
        <div className="card mb-5 border-red-400/30 p-4 text-sm text-red-300">{error}</div>
      )}
      {notice && (
        <div className="card mb-5 border-teal/40 bg-teal-soft p-4 text-sm text-teal">{notice}</div>
      )}

      {tab === "overview" && overview && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Total users" value={overview.users.total} />
            <StatCard
              label="Paying users"
              value={
                (overview.users.by_tier.builder ?? 0) +
                (overview.users.by_tier.pro ?? 0) +
                (overview.users.by_tier.enterprise ?? 0)
              }
            />
            <StatCard label="Public blueprints" value={overview.blueprints.public} />
            <StatCard label="Enriched blueprints" value={overview.blueprints.enriched} />
            <StatCard label="Raw patents" value={overview.raw_patents} />
            <StatCard label="Community posts" value={overview.community_posts} />
            <StatCard label="FTO ready" value={overview.fto_reports.ready ?? 0} />
            <StatCard label="FTO failed" value={overview.fto_reports.failed ?? 0} />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="card p-5">
              <p className="section-label mb-3">Users by tier</p>
              {Object.entries(overview.users.by_tier).map(([tier, count]) => (
                <div key={tier} className="flex justify-between py-1 text-sm">
                  <span className="capitalize text-muted">{tier}</span>
                  <span className="font-medium tabular-nums">{count}</span>
                </div>
              ))}
            </div>
            <div className="card p-5">
              <p className="section-label mb-3">Usage (last 30 days)</p>
              {Object.entries(overview.usage_last_30d).length === 0 && (
                <p className="text-sm text-muted">No events yet.</p>
              )}
              {Object.entries(overview.usage_last_30d).map(([type, count]) => (
                <div key={type} className="flex justify-between py-1 text-sm">
                  <span className="text-muted">{type}</span>
                  <span className="font-medium tabular-nums">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "messages" && (
        <div className="gap-5 lg:grid lg:grid-cols-[300px_1fr]">
          {/* Thread list */}
          <div>
            <div className="mb-3 flex gap-1">
              {(["open", "closed", "all"] as const).map((filter) => (
                <button
                  key={filter}
                  onClick={() => {
                    setThreadFilter(filter);
                    setActiveThread(null);
                  }}
                  className={clsx(
                    "rounded-full border px-3 py-1 text-xs capitalize transition",
                    threadFilter === filter
                      ? "border-accent/50 bg-accent-soft text-accent"
                      : "border-edge text-muted hover:text-ink"
                  )}
                >
                  {filter}
                </button>
              ))}
            </div>
            <div className="card max-h-[520px] divide-y divide-edge overflow-y-auto">
              {threads.map((thread) => (
                <button
                  key={thread.id}
                  onClick={() => openThread(thread)}
                  className={clsx(
                    "block w-full p-3.5 text-left transition hover:bg-raised/50",
                    activeThread?.id === thread.id && "bg-raised/60"
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm font-semibold">
                      {thread.email ?? thread.user_id.slice(0, 8)}
                    </p>
                    {thread.unread > 0 && (
                      <span className="flex h-5 min-w-5 flex-none items-center justify-center rounded-full bg-accent px-1 text-[11px] font-bold text-base">
                        {thread.unread}
                      </span>
                    )}
                  </div>
                  <p className="mt-0.5 truncate text-xs text-muted">
                    {thread.subject ?? "(no subject)"}
                  </p>
                  <p className="mt-0.5 text-[10px] text-muted">
                    {thread.tier} · {new Date(thread.last_message_at).toLocaleString()}
                  </p>
                </button>
              ))}
              {threads.length === 0 && (
                <p className="p-6 text-sm text-muted">No {threadFilter} conversations.</p>
              )}
            </div>
          </div>

          {/* Conversation */}
          <div className="mt-5 lg:mt-0">
            {!activeThread ? (
              <div className="card flex h-full min-h-[240px] items-center justify-center p-8 text-sm text-muted">
                Select a conversation to read and reply.
              </div>
            ) : (
              <div className="card flex max-h-[560px] flex-col">
                <div className="flex items-center justify-between border-b border-edge p-4">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold">
                      {activeThread.email ?? activeThread.user_id}
                    </p>
                    <p className="text-xs text-muted">{activeThread.subject}</p>
                  </div>
                  <button
                    className="btn-ghost flex-none px-3 py-1.5 text-xs"
                    disabled={busy === "thread-status"}
                    onClick={() =>
                      act("thread-status", async () => {
                        const next =
                          activeThread.status === "open" ? "closed" : "open";
                        await adminSupportSetStatus(activeThread.id, next);
                        setActiveThread({ ...activeThread, status: next });
                        load("messages");
                      })
                    }
                  >
                    {activeThread.status === "open" ? "Close" : "Reopen"}
                  </button>
                </div>
                <div className="flex-1 space-y-3 overflow-y-auto p-4">
                  {threadMessages.map((message) => (
                    <div
                      key={message.id}
                      className={clsx(
                        "max-w-[85%] rounded-xl px-3.5 py-2.5 text-sm leading-relaxed",
                        message.sender === "admin"
                          ? "ml-auto bg-accent-soft"
                          : "bg-raised"
                      )}
                    >
                      {message.body}
                      <p className="mt-1 text-[10px] text-muted">
                        {message.sender === "admin" ? "You · " : "User · "}
                        {new Date(message.created_at).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
                <form
                  className="flex gap-2 border-t border-edge p-3"
                  onSubmit={(event) => {
                    event.preventDefault();
                    const body = reply.trim();
                    if (!body) return;
                    act("reply", async () => {
                      const { message } = await adminSupportReply(
                        activeThread.id,
                        body
                      );
                      setThreadMessages((current) => [...current, message]);
                      setReply("");
                    });
                  }}
                >
                  <input
                    className="input flex-1 py-2"
                    placeholder="Reply to the customer... (they also get an email)"
                    value={reply}
                    maxLength={2000}
                    onChange={(event) => setReply(event.target.value)}
                  />
                  <button
                    type="submit"
                    disabled={busy === "reply" || !reply.trim()}
                    className="btn-accent px-3 py-2"
                    aria-label="Send reply"
                  >
                    {busy === "reply" ? (
                      <Loader2 className="animate-spin" size={16} />
                    ) : (
                      <Send size={16} />
                    )}
                  </button>
                </form>
              </div>
            )}
          </div>
        </div>
      )}

      {(tab === "blueprints" || tab === "users") && (
        <form
          className="mb-4 flex gap-2"
          onSubmit={(event) => {
            event.preventDefault();
            load(tab, query);
          }}
        >
          <input
            className="input max-w-xs"
            placeholder={tab === "users" ? "Search by email..." : "Search by title..."}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button className="btn-ghost" type="submit">Search</button>
        </form>
      )}

      {tab === "blueprints" && (
        <div className="card divide-y divide-edge overflow-x-auto">
          {blueprints.map((blueprint) => (
            <div key={blueprint.id} className="flex min-w-[560px] items-center gap-4 p-4">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{blueprint.title}</p>
                <p className="mt-0.5 text-xs text-muted">
                  {blueprint.domain} · {blueprint.patent_number ?? "no patent"} · build{" "}
                  {blueprint.buildability_score ?? "—"} · validation{" "}
                  {blueprint.validation_score ?? "—"}
                </p>
              </div>
              <button
                className={clsx(
                  "flex-none rounded-full border px-3 py-1 text-xs font-medium transition",
                  blueprint.is_public
                    ? "border-teal/40 bg-teal-soft text-teal"
                    : "border-edge text-muted"
                )}
                disabled={busy === `vis-${blueprint.id}`}
                onClick={() =>
                  act(`vis-${blueprint.id}`, async () => {
                    await adminUpdateBlueprint(blueprint.id, {
                      is_public: !blueprint.is_public,
                    });
                    load("blueprints", query);
                  })
                }
              >
                {blueprint.is_public ? "Public" : "Hidden"}
              </button>
              <button
                className="flex-none rounded-lg p-2 text-muted transition hover:text-red-300"
                title="Delete blueprint permanently"
                disabled={busy === `del-${blueprint.id}`}
                onClick={() => {
                  if (!window.confirm(`Permanently delete "${blueprint.title}"?`)) return;
                  act(`del-${blueprint.id}`, async () => {
                    await adminDeleteBlueprint(blueprint.id);
                    load("blueprints", query);
                  });
                }}
              >
                <Trash2 size={15} />
              </button>
            </div>
          ))}
          {blueprints.length === 0 && (
            <p className="p-6 text-sm text-muted">No blueprints found.</p>
          )}
        </div>
      )}

      {tab === "users" && (
        <div className="card divide-y divide-edge overflow-x-auto">
          {users.map((user) => (
            <div key={user.id} className="flex min-w-[560px] items-center gap-4 p-4">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{user.email ?? user.id}</p>
                <p className="mt-0.5 text-xs text-muted">
                  joined {new Date(user.created_at).toLocaleDateString()} · searches{" "}
                  {user.monthly_search_count} · validator {user.monthly_validate_count} · API{" "}
                  {user.monthly_api_count}
                </p>
              </div>
              <select
                className="input w-32 flex-none py-1.5 text-xs"
                value={user.tier}
                disabled={busy === `tier-${user.id}`}
                onChange={(event) =>
                  act(`tier-${user.id}`, async () => {
                    await adminUpdateUser(user.id, { tier: event.target.value });
                    load("users", query);
                  })
                }
              >
                {["free", "builder", "pro", "enterprise"].map((tier) => (
                  <option key={tier} value={tier}>{tier}</option>
                ))}
              </select>
              <button
                className={clsx(
                  "flex-none rounded-full border px-3 py-1 text-xs font-medium transition",
                  user.is_admin
                    ? "border-accent/50 bg-accent-soft text-accent"
                    : "border-edge text-muted"
                )}
                disabled={busy === `adm-${user.id}`}
                onClick={() =>
                  act(`adm-${user.id}`, async () => {
                    await adminUpdateUser(user.id, { is_admin: !user.is_admin });
                    load("users", query);
                  })
                }
              >
                {user.is_admin ? "Admin" : "Member"}
              </button>
            </div>
          ))}
          {users.length === 0 && <p className="p-6 text-sm text-muted">No users found.</p>}
        </div>
      )}

      {tab === "fto" && (
        <div className="card divide-y divide-edge">
          {fto.map((report) => (
            <div key={report.id} className="flex items-center justify-between gap-4 p-4">
              <div className="min-w-0">
                <p className="font-mono text-sm font-semibold">{report.patent_number}</p>
                <p className="mt-0.5 truncate text-xs text-muted">
                  {new Date(report.created_at).toLocaleString()} · user {report.user_id.slice(0, 8)}
                  {report.error ? ` · ${report.error.slice(0, 80)}` : ""}
                </p>
              </div>
              <span className="flex-none rounded-full border border-edge px-2.5 py-1 text-xs text-muted">
                {report.status}
              </span>
            </div>
          ))}
          {fto.length === 0 && <p className="p-6 text-sm text-muted">No reports yet.</p>}
        </div>
      )}

      {tab === "ops" && (
        <div className="space-y-6">
          <div className="grid gap-3 sm:grid-cols-2">
            {OPS_TASKS.map((task) => (
              <div key={task.name} className="card flex items-center justify-between gap-4 p-4">
                <div>
                  <p className="text-sm font-semibold">{task.label}</p>
                  <p className="mt-0.5 text-xs text-muted">{task.detail}</p>
                </div>
                <button
                  className="btn-ghost flex-none px-3 py-1.5 text-xs"
                  disabled={busy === `task-${task.name}`}
                  onClick={() =>
                    act(
                      `task-${task.name}`,
                      async () => {
                        await adminRunTask(task.name);
                      },
                      `Started: ${task.label}. Watch the runs log below.`
                    )
                  }
                >
                  {busy === `task-${task.name}` ? (
                    <Loader2 className="animate-spin" size={13} />
                  ) : (
                    <Play size={13} />
                  )}
                  Run
                </button>
              </div>
            ))}
          </div>
          <div>
            <p className="section-label mb-3">Recent ingestion runs</p>
            <div className="card divide-y divide-edge overflow-x-auto">
              {runs.map((run) => (
                <div key={String(run.id)} className="flex min-w-[480px] items-center justify-between gap-4 p-3.5 text-sm">
                  <span className="font-mono text-xs">{String(run.source ?? "?")}</span>
                  <span className="text-xs text-muted">
                    fetched {String(run.fetched ?? 0)} · inserted {String(run.inserted ?? 0)} ·
                    translated {String(run.translated ?? 0)} · failed {String(run.failed ?? 0)}
                  </span>
                  <span className="text-xs text-muted">
                    {run.started_at ? new Date(String(run.started_at)).toLocaleString() : ""}
                  </span>
                </div>
              ))}
              {runs.length === 0 && <p className="p-6 text-sm text-muted">No runs logged yet.</p>}
            </div>
          </div>
        </div>
      )}

      {tab === "footer" && footer && (
        <form
          className="card max-w-2xl space-y-4 p-6"
          onSubmit={(event) => {
            event.preventDefault();
            act(
              "save-footer",
              async () => {
                const saved = await adminSaveFooter(footer);
                setFooter(saved.footer);
              },
              "Footer saved. Live within 5 minutes (cached)."
            );
          }}
        >
          <p className="text-sm text-muted">
            This content renders in the site footer and feeds the contact lines
            on the policy pages.
          </p>
          {(
            [
              ["company_name", "Company name"],
              ["product_name", "Product name"],
              ["tagline", "Tagline"],
              ["address", "Address"],
              ["contact_email", "Contact email"],
            ] as const
          ).map(([key, label]) => (
            <div key={key}>
              <label className="mb-1.5 block text-xs font-medium text-muted">{label}</label>
              <input
                className="input"
                value={footer[key]}
                onChange={(event) => setFooter({ ...footer, [key]: event.target.value })}
              />
            </div>
          ))}
          <div>
            <label className="mb-1.5 block text-xs font-medium text-muted">
              Extra links (label + URL)
            </label>
            {[...footer.links, { label: "", url: "" }].slice(0, 6).map((link, index) => (
              <div key={index} className="mb-2 flex gap-2">
                <input
                  className="input w-40"
                  placeholder="Label"
                  value={link.label}
                  onChange={(event) => {
                    const links = [...footer.links];
                    links[index] = { ...(links[index] ?? { url: "" }), label: event.target.value };
                    setFooter({ ...footer, links: links.filter((l) => l.label || l.url) });
                  }}
                />
                <input
                  className="input flex-1"
                  placeholder="https://..."
                  value={link.url}
                  onChange={(event) => {
                    const links = [...footer.links];
                    links[index] = { ...(links[index] ??  { label: "" }), url: event.target.value };
                    setFooter({ ...footer, links: links.filter((l) => l.label || l.url) });
                  }}
                />
              </div>
            ))}
          </div>
          <button type="submit" disabled={busy === "save-footer"} className="btn-accent">
            {busy === "save-footer" && <Loader2 className="animate-spin" size={15} />}
            Save Footer
          </button>
        </form>
      )}
    </div>
  );
}
