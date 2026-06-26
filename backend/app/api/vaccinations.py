"""Vaccination router.

Two surfaces:
  * The generic reference schedule + an in-memory administered log (Phase 1).
  * A **birthday-relative tracker** that computes each milestone dose's due date
    from an infant's ``birth_date`` and flags it OVERDUE / UPCOMING / SAFE.
"""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.infants import find_infant
from app.core.database import get_supabase

router = APIRouter(prefix="/api/vaccinations", tags=["vaccinations"])


# ---------------------------------------------------------------------------
# Generic reference schedule + administered log
# ---------------------------------------------------------------------------
class ScheduledVaccine(BaseModel):
    """A vaccine in the recommended schedule."""

    code: str
    name: str
    recommended_age_months: int = Field(..., ge=0, le=216)


# Illustrative schedule. Replace with a locale-aware, sourced schedule.
_SCHEDULE: list[ScheduledVaccine] = [
    ScheduledVaccine(code="HepB-1", name="Hepatitis B (1st dose)", recommended_age_months=0),
    ScheduledVaccine(code="DTaP-1", name="DTaP (1st dose)", recommended_age_months=2),
    ScheduledVaccine(code="IPV-1", name="Polio (1st dose)", recommended_age_months=2),
    ScheduledVaccine(code="MMR-1", name="MMR (1st dose)", recommended_age_months=12),
    ScheduledVaccine(code="VAR-1", name="Varicella (1st dose)", recommended_age_months=12),
]


class VaccinationLogCreate(BaseModel):
    """A record that a vaccine was administered."""

    infant_id: str
    code: str = Field(..., description="Vaccine code from the schedule, e.g. 'DTaP-1'.")
    administered_on: date = Field(default_factory=date.today)


class VaccinationLog(VaccinationLogCreate):
    """A persisted vaccination log entry."""

    id: str


# In-memory fallback used only when Supabase is not configured.
_LOGS: list[VaccinationLog] = []
_LOGS_TABLE = "vaccination_logs"


def _row_to_log(row: dict) -> VaccinationLog:
    return VaccinationLog(
        id=str(row["id"]),
        infant_id=str(row["infant_id"]),
        code=row["code"],
        administered_on=row["administered_on"],
    )


# ---------------------------------------------------------------------------
# Birthday-relative tracker
# ---------------------------------------------------------------------------
VaccineStatus = Literal["COMPLETED", "OVERDUE", "UPCOMING", "SAFE"]

# Standard milestone doses, keyed by age in months. Source: a simplified view
# of the CDC infant immunization schedule (replace with a locale-aware set).
_MILESTONE_SCHEDULE: tuple[tuple[int, str, str], ...] = (
    (0, "HepB-1", "Hepatitis B (Dose 1)"),
    (2, "RV-1", "Rotavirus (Dose 1)"),
    (2, "DTaP-1", "DTaP (Dose 1)"),
    (2, "Hib-1", "Hib (Dose 1)"),
    (2, "PCV13-1", "PCV13 (Dose 1)"),
    (2, "IPV-1", "Polio / IPV (Dose 1)"),
    (4, "DTaP-2", "DTaP (Dose 2)"),
    (4, "Hib-2", "Hib (Dose 2)"),
    (4, "PCV13-2", "PCV13 (Dose 2)"),
    (4, "IPV-2", "Polio / IPV (Dose 2)"),
)

# A dose due within this window (computed with ``timedelta``) is "UPCOMING".
_UPCOMING_WINDOW = timedelta(days=30)


class VaccineDueItem(BaseModel):
    """A single milestone dose with its computed due date and status."""

    code: str
    name: str
    age_months: int
    due_date: date
    status: VaccineStatus


class InfantVaccineSchedule(BaseModel):
    """The personalized, date-resolved vaccination plan for one infant."""

    infant_id: str
    birth_date: date
    generated_on: date
    items: list[VaccineDueItem]


def _add_months(start: date, months: int) -> date:
    """Add calendar months to a date, clamping the day for short months.

    "2 months" / "4 months" are calendar intervals, so we advance the month
    field rather than approximating with a fixed number of days.
    """
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))


def _status_for(due: date, today: date) -> VaccineStatus:
    """Bucket a due date relative to today using a ``timedelta`` window."""
    if due < today:
        return "OVERDUE"
    if due <= today + _UPCOMING_WINDOW:
        return "UPCOMING"
    return "SAFE"


# ---------------------------------------------------------------------------
# Routes — literal paths declared BEFORE the /{infant_id} catch-all.
# ---------------------------------------------------------------------------
@router.get("/schedule", response_model=list[ScheduledVaccine])
async def get_schedule() -> list[ScheduledVaccine]:
    """Return the recommended vaccination schedule."""
    return _SCHEDULE


@router.post("/logs", response_model=VaccinationLog, status_code=status.HTTP_201_CREATED)
async def log_vaccination(payload: VaccinationLogCreate) -> VaccinationLog:
    """Record an administered vaccination."""
    sb = get_supabase()
    if sb is not None:
        row = (
            sb.table(_LOGS_TABLE)
            .insert(
                {
                    "infant_id": payload.infant_id,
                    "code": payload.code,
                    "administered_on": payload.administered_on.isoformat(),
                }
            )
            .execute()
            .data[0]
        )
        return _row_to_log(row)

    log = VaccinationLog(id=str(uuid4()), **payload.model_dump())
    _LOGS.append(log)
    return log


@router.get("/logs", response_model=list[VaccinationLog])
async def list_logs(infant_id: str | None = None) -> list[VaccinationLog]:
    """List vaccination logs, optionally filtered by infant."""
    sb = get_supabase()
    if sb is not None:
        query = sb.table(_LOGS_TABLE).select("*")
        if infant_id is not None:
            query = query.eq("infant_id", infant_id)
        return [_row_to_log(r) for r in (query.execute().data or [])]

    if infant_id is None:
        return _LOGS
    return [log for log in _LOGS if log.infant_id == infant_id]


@router.get("/{infant_id}", response_model=InfantVaccineSchedule)
async def infant_vaccine_schedule(infant_id: str) -> InfantVaccineSchedule:
    """Compute the birthday-relative vaccination plan for one infant.

    Each milestone dose's due date is derived from the infant's ``birth_date``
    and compared with today to set an ``OVERDUE`` / ``UPCOMING`` / ``SAFE``
    status.
    """
    infant = find_infant(infant_id)
    if infant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Infant not found")

    today = date.today()

    # Sync with administered logs: any dose already recorded for this infant is
    # marked COMPLETED, overriding the date-derived status.
    sb = get_supabase()
    if sb is not None:
        rows = (
            sb.table(_LOGS_TABLE)
            .select("code")
            .eq("infant_id", infant_id)
            .execute()
            .data
            or []
        )
        administered: set[str] = {r["code"] for r in rows}
    else:
        administered = {log.code for log in _LOGS if log.infant_id == infant_id}

    items = [
        VaccineDueItem(
            code=code,
            name=name,
            age_months=months,
            due_date=(due := _add_months(infant.birth_date, months)),
            status="COMPLETED" if code in administered else _status_for(due, today),
        )
        for months, code, name in _MILESTONE_SCHEDULE
    ]

    return InfantVaccineSchedule(
        infant_id=infant.id,
        birth_date=infant.birth_date,
        generated_on=today,
        items=items,
    )
