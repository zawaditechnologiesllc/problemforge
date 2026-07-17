import { getAccessToken } from "@/lib/supabase/client";
import type {
  ApiKey,
  BlueprintDetail,
  BlueprintSummary,
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
  return request<{ method: string; matches: ValidatorMatch[] }>(
    "/api/v1/validate",
    { method: "POST", body: { idea } }
  );
}

export function getMe() {
  return request<Me>("/api/v1/account/me");
}

export function getSaved() {
  return request<{ items: BlueprintSummary[] }>("/api/v1/account/saved");
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
