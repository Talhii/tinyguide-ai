"""Growth analytics router.

Exposes the stubbed ``/api/analytics/growth-percentile`` endpoint that accepts
weight/height inputs and runs them through the WHO percentile service.
"""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.api.infants import find_infant
from app.core.database import get_supabase
from app.core.security import Gender
from app.services.percentile import calculate_percentile, reference_band

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Average Gregorian month length, used to derive age-in-months from dates.
_DAYS_PER_MONTH = 30.4375


class GrowthInput(BaseModel):
    """Measurement inputs for a percentile lookup."""

    gender: Gender
    age_months: float = Field(..., ge=0, le=60, description="Age in months (0–60).")
    weight_kg: float | None = Field(None, gt=0, description="Weight in kilograms.")
    height_cm: float | None = Field(None, gt=0, description="Height/length in centimeters.")


class MetricResult(BaseModel):
    """Single-metric percentile result."""

    metric: str
    z_score: float
    percentile: float
    reference_median: float
    interpretation: str


class GrowthResult(BaseModel):
    """Aggregated percentile results for the submitted measurements."""

    age_months: float
    results: list[MetricResult]


@router.post("/growth-percentile", response_model=GrowthResult)
async def growth_percentile(payload: GrowthInput) -> GrowthResult:
    """Compute WHO percentiles for the provided weight and/or height.

    This is a Phase 1 placeholder formula: it uses the WHO LMS method against a
    small illustrative reference table (see ``services/percentile.py``). At
    least one of ``weight_kg`` or ``height_cm`` should be supplied.
    """
    results: list[MetricResult] = []

    if payload.weight_kg is not None:
        results.append(
            MetricResult(
                **calculate_percentile(
                    gender=payload.gender,
                    metric="weight",
                    age_months=payload.age_months,
                    value=payload.weight_kg,
                )
            )
        )

    if payload.height_cm is not None:
        results.append(
            MetricResult(
                **calculate_percentile(
                    gender=payload.gender,
                    metric="height",
                    age_months=payload.age_months,
                    value=payload.height_cm,
                )
            )
        )

    return GrowthResult(age_months=payload.age_months, results=results)


# ---------------------------------------------------------------------------
# Growth entry logs — live measurement storage
# ---------------------------------------------------------------------------
class GrowthLogCreate(BaseModel):
    """Payload for logging a single measurement."""

    infant_id: str
    weight_kg: float = Field(..., gt=0, description="Weight in kilograms (> 0).")
    height_cm: float = Field(..., gt=0, description="Height/length in cm (> 0).")
    recorded_at: date | None = Field(
        None, description="Measurement date (defaults to today; cannot be future)."
    )

    @field_validator("recorded_at")
    @classmethod
    def not_in_future(cls, value: date | None) -> date | None:
        if value is not None and value > date.today():
            raise ValueError("recorded_at cannot be in the future")
        return value


class GrowthLogEntry(GrowthLogCreate):
    """A persisted growth measurement."""

    id: str
    recorded_at: date


# In-memory fallback used only when Supabase is not configured.
_GROWTH_LOGS: dict[str, list[GrowthLogEntry]] = {}
_GROWTH_TABLE = "growth_logs"


@router.post(
    "/growth-log",
    response_model=GrowthLogEntry,
    status_code=status.HTTP_201_CREATED,
)
async def log_growth(payload: GrowthLogCreate) -> GrowthLogEntry:
    """Record a weight/height measurement for an infant."""
    if find_infant(payload.infant_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Infant not found"
        )

    recorded_at = payload.recorded_at or date.today()
    sb = get_supabase()
    if sb is not None:
        row = (
            sb.table(_GROWTH_TABLE)
            .insert(
                {
                    "infant_id": payload.infant_id,
                    "weight_kg": payload.weight_kg,
                    "height_cm": payload.height_cm,
                    "recorded_at": recorded_at.isoformat(),
                }
            )
            .execute()
            .data[0]
        )
        return GrowthLogEntry(
            id=str(row["id"]),
            infant_id=str(row["infant_id"]),
            weight_kg=float(row["weight_kg"]),
            height_cm=float(row["height_cm"]),
            recorded_at=row["recorded_at"],
        )

    entry = GrowthLogEntry(
        id=str(uuid4()),
        infant_id=payload.infant_id,
        weight_kg=payload.weight_kg,
        height_cm=payload.height_cm,
        recorded_at=recorded_at,
    )
    _GROWTH_LOGS.setdefault(payload.infant_id, []).append(entry)
    return entry


# ---------------------------------------------------------------------------
# Growth velocity engine — timeline of logged measurements vs WHO bands
# ---------------------------------------------------------------------------
class GrowthTimelineInput(BaseModel):
    """Request the growth timeline for one infant."""

    infant_id: str


class GrowthPlotPoint(BaseModel):
    """A single timeline point: the child's value plus WHO percentile bands."""

    age_months: float
    child_weight: float
    p5_weight: float
    p50_weight: float
    p95_weight: float


class GrowthTimeline(BaseModel):
    """The full growth trajectory, ready to plot."""

    gender: Gender
    birth_date: date
    points: list[GrowthPlotPoint]


@router.post("/growth-timeline", response_model=GrowthTimeline)
async def growth_timeline(payload: GrowthTimelineInput) -> GrowthTimeline:
    """Build a growth trajectory from the infant's **live** logged measurements.

    Each logged entry's age (in months) is computed from the infant's
    ``birth_date``, then the WHO LMS reference band is evaluated at that exact
    age and gender so the percentile tracks bend with the child's age. When no
    measurements have been logged yet, ``points`` is an empty array so the UI
    can show a clean setup callout.
    """
    infant = find_infant(payload.infant_id)
    if infant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Infant not found"
        )

    # Gather (recorded_at, weight) pairs from Supabase or the in-memory store.
    sb = get_supabase()
    if sb is not None:
        rows = (
            sb.table(_GROWTH_TABLE)
            .select("recorded_at, weight_kg")
            .eq("infant_id", payload.infant_id)
            .order("recorded_at")
            .execute()
            .data
            or []
        )
        measurements = [
            (date.fromisoformat(r["recorded_at"]), float(r["weight_kg"])) for r in rows
        ]
    else:
        measurements = [
            (e.recorded_at, e.weight_kg)
            for e in sorted(
                _GROWTH_LOGS.get(payload.infant_id, []), key=lambda e: e.recorded_at
            )
        ]

    points: list[GrowthPlotPoint] = []
    for recorded_at, weight in measurements:
        age_days = max((recorded_at - infant.birth_date).days, 0)
        age_months = round(age_days / _DAYS_PER_MONTH, 1)
        band = reference_band(
            gender=infant.gender, metric="weight", age_months=age_months
        )
        points.append(
            GrowthPlotPoint(
                age_months=age_months,
                child_weight=weight,
                p5_weight=band[5],
                p50_weight=band[50],
                p95_weight=band[95],
            )
        )

    return GrowthTimeline(
        gender=infant.gender, birth_date=infant.birth_date, points=points
    )
