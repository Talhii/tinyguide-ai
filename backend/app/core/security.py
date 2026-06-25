"""Security schemas and shared Pydantic primitives.

Holds the enums and base models reused across routers so validation rules live
in exactly one place. Auth/token plumbing will hang off ``CurrentUser`` once
Supabase auth is wired in.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Gender(str, Enum):
    """Infant gender — drives WHO percentile chart selection."""

    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class CurrentUser(BaseModel):
    """Placeholder identity object resolved from a Supabase JWT.

    Wire this into routes via a FastAPI dependency once auth is enabled.
    """

    id: str = Field(..., description="Supabase auth user id (UUID).")
    email: str | None = Field(None, description="User email, if available.")


class HealthStatus(BaseModel):
    """Standard health-check payload."""

    status: str = "ok"
    service: str = "TinyGuide AI"
    version: str
