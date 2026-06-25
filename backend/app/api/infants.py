"""Infant registration router.

Pydantic-validated CRUD surface for registering a child profile. Persistence is
stubbed in-memory for Phase 1; swap ``_REGISTRY`` for Supabase once configured.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.core.security import Gender

router = APIRouter(prefix="/api/infants", tags=["infants"])


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


# In-memory registry for Phase 1. Replace with Supabase persistence.
_REGISTRY: dict[str, Infant] = {}


def find_infant(infant_id: str) -> Infant | None:
    """Look up a registered infant by id (used by other routers)."""
    return _REGISTRY.get(infant_id)


@router.post("", response_model=Infant, status_code=status.HTTP_201_CREATED)
async def register_infant(payload: InfantCreate) -> Infant:
    """Register a new infant profile."""
    infant = Infant(id=str(uuid4()), **payload.model_dump())
    _REGISTRY[infant.id] = infant
    return infant


@router.get("", response_model=list[Infant])
async def list_infants() -> list[Infant]:
    """List all registered infants."""
    return list(_REGISTRY.values())


@router.get("/{infant_id}", response_model=Infant)
async def get_infant(infant_id: str) -> Infant:
    """Fetch a single infant by id."""
    infant = _REGISTRY.get(infant_id)
    if infant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Infant not found")
    return infant


@router.put("/{infant_id}", response_model=Infant)
async def update_infant(infant_id: str, payload: InfantCreate) -> Infant:
    """Update an existing infant's profile."""
    if infant_id not in _REGISTRY:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Infant not found")
    updated = Infant(id=infant_id, **payload.model_dump())
    _REGISTRY[infant_id] = updated
    return updated
