from supabase import Client, create_client

from .config import settings

_client: Client | None = None


def get_db() -> Client:
    """Service-role Supabase client (bypasses RLS — server-side only)."""
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )
        _client = create_client(
            settings.supabase_url, settings.supabase_service_role_key
        )
    return _client
