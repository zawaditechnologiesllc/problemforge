from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration comes from environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    frontend_url: str = "http://localhost:3000"

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    # Optional legacy HS256 JWT secret. If unset, tokens are verified by
    # calling the Supabase Auth API (works with new asymmetric-key projects).
    supabase_jwt_secret: str = ""

    # Stripe
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_builder: str = ""     # $19/mo plan price id
    stripe_price_pro: str = ""         # $49/mo plan price id
    stripe_price_enterprise: str = ""  # $150/mo plan price id
    stripe_price_fto: str = ""         # $99 one-time Freedom-to-Operate report

    # LLM (OpenAI-compatible aggregator — OpenRouter/DeepInfra/SiliconFlow)
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    translator_model: str = "deepseek/deepseek-v4-flash"  # bulk patent -> blueprint translation
    coder_model: str = "qwen/qwen-3-coder"                # user-facing prompt/code generation

    # Embeddings (separate because most aggregators don't serve embeddings)
    embeddings_base_url: str = "https://api.openai.com/v1"
    embeddings_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"  # 1536 dims, matches the schema

    # Patent sources — each activates automatically when its credentials exist
    uspto_api_key: str = ""                # PatentsView API key (free at patentsview.org)
    google_service_account_json: str = ""  # GCP service-account JSON (BigQuery public patents)
    lens_api_key: str = ""                 # Lens.org API token
    epo_ops_key: str = ""                  # EPO OPS consumer key
    epo_ops_secret: str = ""               # EPO OPS consumer secret

    # Freedom-to-Operate reports
    fto_bucket: str = "fto-reports"  # private Supabase Storage bucket for PDFs


settings = Settings()
