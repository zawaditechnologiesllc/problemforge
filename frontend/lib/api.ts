import { getAccessToken } from "@/lib/supabase/client";
import type {
  ActiveLandscape,
  AdminBlueprint,
  AdminOverview,
  AdminSupportThread,
  AdminUser,
  ApiKey,
  FooterSettingsData,
  SupportMessage,
  SupportThreadInfo,
  BlueprintDetail,
  BlueprintSummary,
  CommunityMatch,
  CommunityQuestion,
  FrameworkAnalysis,
  FtoReport,
  Me,
  ValidatorMatch,
} from "@/lib/types";

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(status: number, message: string, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean } = {}
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (options.auth !== false) {
    const token = await getAccessToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${API_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    let code: string | undefined;
    try {
      const data = await response.json();
      const detail = data?.detail;
      if (typeof detail === "string") message = detail;
      else if (detail?.message) {
        message = detail.message;
        code = detail.code;
      }
    } catch {
      // keep default message
    }
    throw new ApiError(response.status, message, code);
  }
  return response.json() as Promise<T>;
}

export interface ListParams {
  q?: string;
  domain?: string;
  min_buildability?: number;
  public_domain_only?: boolean;
  sort?: string;
  limit?: number;
  offset?: number;
}

export function listBlueprints(params: ListParams) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== false) {
      search.set(key, String(value));
    }
  });
  return request<{ items: BlueprintSummary[]; total: number }>(
    `/api/v1/blueprints?${search.toString()}`
  );
}

export function getBlueprint(id: string) {
  return request<BlueprintDetail>(`/api/v1/blueprints/${id}`);
}

export function getRelated(id: string) {
  return request<{ items: BlueprintSummary[] }>(
    `/api/v1/blueprints/${id}/related`
  );
}

export function logPromptCopy(id: string) {
  return request<{ master_prompt: string }>(`/api/v1/blueprints/${id}/copy`, {
    method: "POST",
  });
}

export function saveBlueprint(id: string) {
  return request<{ saved: boolean }>(`/api/v1/blueprints/${id}/save`, {
    method: "POST",
  });
}

export function unsaveBlueprint(id: string) {
  return request<{ saved: boolean }>(`/api/v1/blueprints/${id}/save`, {
    method: "DELETE",
  });
}

export function validateIdea(idea: string) {
  return request<{
    method: string;
    matches: ValidatorMatch[];
    active_landscape: ActiveLandscape | null;
    community_questions: CommunityQuestion[];
    community_matches: CommunityMatch[];
    framework: FrameworkAnalysis | null;
  }>("/api/v1/validate", { method: "POST", body: { idea } });
}

export function getMe() {
  return request<Me>("/api/v1/account/me");
}

export function getSaved() {
  return request<{ items: BlueprintSummary[] }>("/api/v1/account/saved");
}

export function deleteAccount() {
  return request<{ deleted: boolean }>("/api/v1/account", { method: "DELETE" });
}

export function createCheckout(plan: "builder" | "pro" | "enterprise") {
  return request<{ url: string }>("/api/v1/billing/checkout", {
    method: "POST",
    body: { plan },
  });
}

export function openPortal() {
  return request<{ url: string }>("/api/v1/billing/portal", { method: "POST" });
}

export function ftoCheckout(body: {
  patent_number?: string;
  blueprint_id?: string;
}) {
  return request<{ url: string; report_id: string }>("/api/v1/fto/checkout", {
    method: "POST",
    body,
  });
}

export function listFtoReports() {
  return request<{ items: FtoReport[] }>("/api/v1/fto/reports");
}

export function getFtoDownload(id: string) {
  return request<{ url: string }>(`/api/v1/fto/reports/${id}/download`);
}

export function retryFtoReport(id: string) {
  return request<{ queued: boolean }>(`/api/v1/fto/reports/${id}/retry`, {
    method: "POST",
  });
}

// ---- Admin panel ----

export function adminOverview() {
  return request<AdminOverview>("/api/v1/admin/overview");
}

export function adminUsers(q?: string, offset = 0) {
  const search = new URLSearchParams({ offset: String(offset) });
  if (q) search.set("q", q);
  return request<{ items: AdminUser[]; total: number }>(
    `/api/v1/admin/users?${search.toString()}`
  );
}

export function adminUpdateUser(
  id: string,
  body: { tier?: string; is_admin?: boolean }
) {
  return request<AdminUser>(`/api/v1/admin/users/${id}`, {
    method: "PATCH",
    body,
  });
}

export function adminBlueprints(q?: string, offset = 0) {
  const search = new URLSearchParams({ offset: String(offset) });
  if (q) search.set("q", q);
  return request<{ items: AdminBlueprint[]; total: number }>(
    `/api/v1/admin/blueprints?${search.toString()}`
  );
}

export function adminUpdateBlueprint(
  id: string,
  body: Partial<
    Pick<
      AdminBlueprint,
      "title" | "domain" | "buildability_score" | "demand_signal_score" | "is_public"
    >
  >
) {
  return request<AdminBlueprint>(`/api/v1/admin/blueprints/${id}`, {
    method: "PATCH",
    body,
  });
}

export function adminDeleteBlueprint(id: string) {
  return request<{ deleted: boolean }>(`/api/v1/admin/blueprints/${id}`, {
    method: "DELETE",
  });
}

export function adminFtoReports() {
  return request<{ items: (FtoReport & { user_id: string })[] }>(
    "/api/v1/admin/fto-reports"
  );
}

export function adminIngestionRuns() {
  return request<{ items: Record<string, unknown>[] }>(
    "/api/v1/admin/ingestion-runs"
  );
}

export function adminRunTask(name: string) {
  return request<{ started: string }>(`/api/v1/admin/tasks/${name}`, {
    method: "POST",
  });
}

export function fetchSiteSettings() {
  return request<{ footer: FooterSettingsData }>("/api/v1/site-settings", {
    auth: false,
  });
}

export function adminSaveFooter(footer: FooterSettingsData) {
  return request<{ footer: FooterSettingsData }>("/api/v1/admin/settings/footer", {
    method: "PUT",
    body: footer,
  });
}

// ---- Support chat ----

export function getSupportThread(markRead = false) {
  return request<{
    thread: SupportThreadInfo | null;
    messages: SupportMessage[];
    unread: number;
  }>(`/api/v1/support/thread${markRead ? "?mark_read=true" : ""}`);
}

export function sendSupportMessage(body: string) {
  return request<{ message: SupportMessage; thread_id: string }>(
    "/api/v1/support/messages",
    { method: "POST", body: { body } }
  );
}

export function adminSupportThreads(status: "open" | "closed" | "all" = "open") {
  return request<{ items: AdminSupportThread[] }>(
    `/api/v1/admin/support/threads?status=${status}`
  );
}

export function adminSupportThread(id: string) {
  return request<{ thread: AdminSupportThread; messages: SupportMessage[] }>(
    `/api/v1/admin/support/threads/${id}`
  );
}

export function adminSupportReply(id: string, body: string) {
  return request<{ message: SupportMessage }>(
    `/api/v1/admin/support/threads/${id}/reply`,
    { method: "POST", body: { body } }
  );
}

export function adminSupportSetStatus(id: string, status: "open" | "closed") {
  return request<AdminSupportThread>(`/api/v1/admin/support/threads/${id}`, {
    method: "PATCH",
    body: { status },
  });
}

export function listApiKeys() {
  return request<{ items: ApiKey[] }>("/api/v1/account/api-keys");
}

export function createApiKey(name: string) {
  return request<{ key: string }>("/api/v1/account/api-keys", {
    method: "POST",
    body: { name },
  });
}

export function revokeApiKey(id: string) {
  return request<{ revoked: boolean }>(`/api/v1/account/api-keys/${id}`, {
    method: "DELETE",
  });
}
