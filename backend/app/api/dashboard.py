"""Dashboard inputs router.

Accepts the day-to-day caregiver log entries (sleep, feeding, mood) that feed
the dashboard, and returns a lightweight summary. Persistence is stubbed.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from uuid import uuid4

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


class EntryType(str, Enum):
    """Kinds of dashboard log entries."""

    SLEEP = "sleep"
    FEEDING = "feeding"
    MOOD = "mood"


class DashboardEntryCreate(BaseModel):
    """A single caregiver-logged data point."""

    infant_id: str
    entry_type: EntryType
    value: float = Field(..., description="e.g. hours slept, ml fed, mood score 1–5.")
    logged_on: date = Field(default_factory=date.today)
    note: str | None = Field(None, max_length=280)


class DashboardEntry(DashboardEntryCreate):
    """A persisted dashboard entry."""

    id: str


# In-memory store for Phase 1.
_ENTRIES: list[DashboardEntry] = []


@router.post("/entries", response_model=DashboardEntry, status_code=status.HTTP_201_CREATED)
async def create_entry(payload: DashboardEntryCreate) -> DashboardEntry:
    """Record a new dashboard entry."""
    entry = DashboardEntry(id=str(uuid4()), **payload.model_dump())
    _ENTRIES.append(entry)
    return entry


@router.get("/entries", response_model=list[DashboardEntry])
async def list_entries(infant_id: str | None = None) -> list[DashboardEntry]:
    """List dashboard entries, optionally filtered by infant."""
    if infant_id is None:
        return _ENTRIES
    return [e for e in _ENTRIES if e.infant_id == infant_id]
