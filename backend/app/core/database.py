"""Database configuration.

Thin wrapper around the Supabase client. The client is created lazily so the
app can boot (and serve stubbed routes) even before Supabase credentials are
provided — useful during Phase 1 scaffolding.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:  # pragma: no cover - import only for type checkers
    from supabase import Client


@lru_cache
def get_supabase() -> "Client | None":
    """Return a cached Supabase client, or ``None`` if not configured.

    Routes that require persistence should call this and raise a clear error
    when it returns ``None`` rather than failing with an obscure import error.
    """
    if not settings.supabase_url or not settings.supabase_key:
        return None

    # Imported lazily so the dependency is optional during early scaffolding.
    from supabase import create_client

    return create_client(settings.supabase_url, settings.supabase_key)


def require_supabase() -> "Client":
    """Return the Supabase client or raise if it has not been configured."""
    client = get_supabase()
    if client is None:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_KEY "
            "in your environment (see .env.example)."
        )
    return client
