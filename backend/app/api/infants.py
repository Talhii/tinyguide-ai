"""Infant registration router.

Pydantic-validated CRUD for child profiles. Persists to Supabase when
configured (SUPABASE_URL + SUPABASE_KEY); otherwise falls back to an in-memory
store so local development works with no database.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.core.database import get_supabase
from app.core.security import Gender

router = APIRouter(prefix="/api/infants", tags=["infants"])

_TABLE = "infants"


class InfantCreate(BaseModel):
    """Payload for registering a new infant."""

    name: str = Field(..., min_length=1, max_length=120, examples=["Amara"])
    birth_date: date = Field(..., description="Child's date of birth (ISO 8601).")
    gender: Gender = Field(..., description="Used to select WHO growth charts.")

    @field_validator("birth_date")
    @classmethod
    def birth_date_not_future(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("birth_date cannot be in the future")
        return value


class Infant(InfantCreate):
    """A registered infant, including its server-assigned id."""

    id: str = Field(..., description="Server-assigned identifier.")


# In-memory fallback used only when Supabase is not configured.
_REGISTRY: dict[str, Infant] = {}


def _row_to_infant(row: dict) -> Infant:
    return Infant(
        id=str(row["id"]),
        name=row["name"],
        birth_date=row["birth_date"],
        gender=row["gender"],
    )


def _record(payload: InfantCreate) -> dict:
    return {
        "name": payload.name,
        "birth_date": payload.birth_date.isoformat(),
        "gender": payload.gender.value,
    }


def find_infant(infant_id: str) -> Infant | None:
    """Look up a registered infant by id (used by other routers)."""
    sb = get_supabase()
    if sb is not None:
        rows = sb.table(_TABLE).select("*").eq("id", infant_id).limit(1).execute().data
        return _row_to_infant(rows[0]) if rows else None
    return _REGISTRY.get(infant_id)


@router.post("", response_model=Infant, status_code=status.HTTP_201_CREATED)
async def register_infant(payload: InfantCreate) -> Infant:
    """Register a new infant profile."""
    sb = get_supabase()
    if sb is not None:
        row = sb.table(_TABLE).insert(_record(payload)).execute().data[0]
        return _row_to_infant(row)

    infant = Infant(id=str(uuid4()), **payload.model_dump())
    _REGISTRY[infant.id] = infant
    return infant


@router.get("", response_model=list[Infant])
async def list_infants() -> list[Infant]:
    """List all registered infants."""
    sb = get_supabase()
    if sb is not None:
        rows = sb.table(_TABLE).select("*").order("created_at").execute().data or []
        return [_row_to_infant(r) for r in rows]
    return list(_REGISTRY.values())


@router.get("/{infant_id}", response_model=Infant)
async def get_infant(infant_id: str) -> Infant:
    """Fetch a single infant by id."""
    infant = find_infant(infant_id)
    if infant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Infant not found")
    return infant


@router.put("/{infant_id}", response_model=Infant)
async def update_infant(infant_id: str, payload: InfantCreate) -> Infant:
    """Update an existing infant's profile."""
    sb = get_supabase()
    if sb is not None:
        rows = sb.table(_TABLE).update(_record(payload)).eq("id", infant_id).execute().data
        if not rows:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Infant not found")
        return _row_to_infant(rows[0])

    if infant_id not in _REGISTRY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Infant not found")
    updated = Infant(id=infant_id, **payload.model_dump())
    _REGISTRY[infant_id] = updated
    return updated
