export type Domain = "software" | "mechanical" | "medical";

export interface BlueprintSummary {
  id: string;
  title: string;
  domain: Domain;
  patent_number: string | null;
  human_problem: string;
  expired_logic?: string;
  buildability_score: number | null;
  demand_signal_score: number | null;
  validation_score?: number | null;
  public_domain_verified?: boolean;
  created_at: string;
}

export interface PlaybookChannel {
  channel: string;
  audience: string;
  how: string;
}

export interface Playbook {
  problem_today: { still_exists: boolean; assessment: string; evidence: string };
  ai_solution: string;
  stack: {
    design: string;
    coding: string;
    configuration: string;
    integration: string;
    testing: string;
  };
  marketing: { channels: PlaybookChannel[] };
}

export interface CommunityMatch {
  title: string;
  url: string;
  community: string | null;
  upvotes: number;
  num_comments: number;
  similarity: number;
}

export interface BlueprintDetail extends BlueprintSummary {
  expired_logic: string;
  build_plan: string | null;
  master_prompt: string | null;
  playbook: Playbook | null;
  validation: FrameworkAnalysis | null;
  validation_score: number | null;
  enrichment_status: "ready" | "generating" | "pending" | "unavailable";
  locked: boolean;
  saved: boolean;
  patent: {
    patent_number: string;
    filing_date: string | null;
    legal_status: string | null;
    source: string;
  } | null;
}

export interface ActiveLandscape {
  level: "none" | "elevated" | "high";
  note?: string;
}

export interface CommunityQuestion {
  source: "reddit" | "quora";
  title: string;
  url: string;
  community: string | null;
  engagement: number | null;
}

export interface FrameworkPillar {
  score: number;
  assessment: string;
  best_demographic?: string;
  gaps?: string[];
  mvp_scope?: string;
  recommended_model?: string;
  angle?: string;
}

export interface FrameworkAnalysis {
  market_size: FrameworkPillar;
  competition: FrameworkPillar;
  feasibility: FrameworkPillar;
  monetization: FrameworkPillar;
  uniqueness: FrameworkPillar;
  overall_score: number;
  verdict: string;
}

export interface ValidatorMatch {
  id: string;
  title: string;
  domain: Domain;
  patent_number: string | null;
  human_problem: string;
  expired_logic: string;
  buildability_score: number | null;
  demand_signal_score: number | null;
  similarity: number;
}

export interface Me {
  id: string;
  email: string | null;
  tier: "free" | "builder" | "pro" | "enterprise";
  tier_name: string;
  has_billing: boolean;
  usage: {
    searches_used: number;
    searches_limit: number | null; // null = unlimited
    validations_used: number;
    validations_limit: number | null;
    api_requests_used: number;
    api_requests_limit: number | null;
    reset_at: string;
  };
  features: {
    prompts_unlocked: boolean;
    api_access: boolean;
    export: boolean;
    priority_support: boolean;
  };
}

export interface FtoReport {
  id: string;
  patent_number: string;
  blueprint_id: string | null;
  status: "pending_payment" | "queued" | "processing" | "ready" | "failed";
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}
