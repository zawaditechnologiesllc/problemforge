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
  public_domain_verified?: boolean;
  created_at: string;
}

export interface BlueprintDetail extends BlueprintSummary {
  expired_logic: string;
  build_plan: string | null;
  master_prompt: string | null;
  locked: boolean;
  saved: boolean;
  patent: {
    patent_number: string;
    filing_date: string | null;
    legal_status: string | null;
    source: string;
  } | null;
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
  tier: "free" | "builder" | "pro";
  tier_name: string;
  has_billing: boolean;
  usage: {
    searches_used: number;
    searches_limit: number;
    validations_used: number;
    validations_limit: number;
    reset_at: string;
  };
  features: {
    prompts_unlocked: boolean;
    api_access: boolean;
    export: boolean;
  };
}

export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
}
