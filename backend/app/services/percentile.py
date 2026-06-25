"""WHO growth percentile tracking logic.

This is the "core math loop" for the analytics dashboard. It implements the
WHO **LMS method** for converting a raw measurement (weight or height) into a
z-score and percentile against age/gender-standardized reference data.

Phase 1 ships a *placeholder* reference table with a handful of anchor points
and linear interpolation between them. Swap ``_LMS_REFERENCE`` for the full WHO
Child Growth Standards tables to make this production-grade — the public API of
``calculate_percentile`` will not change.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.core.security import Gender


@dataclass(frozen=True)
class LMS:
    """A single WHO LMS reference point.

    L = Box-Cox power, M = median, S = coefficient of variation.
    """

    l: float
    m: float
    s: float


# --- Placeholder reference data ------------------------------------------
# Keyed by (gender, metric) -> {age_in_months: LMS}. These are illustrative
# anchor values, NOT the official WHO tables. Replace with the real dataset.
_LMS_REFERENCE: dict[tuple[Gender, str], dict[int, LMS]] = {
    (Gender.MALE, "weight"): {
        0: LMS(l=0.3487, m=3.3464, s=0.14602),
        6: LMS(l=0.1257, m=7.9340, s=0.11772),
        12: LMS(l=0.0486, m=9.6479, s=0.11080),
        24: LMS(l=-0.0526, m=12.1515, s=0.10958),
    },
    (Gender.MALE, "height"): {
        0: LMS(l=1.0, m=49.8842, s=0.03795),
        6: LMS(l=1.0, m=67.6236, s=0.03165),
        12: LMS(l=1.0, m=75.7488, s=0.03317),
        24: LMS(l=1.0, m=87.1161, s=0.03629),
    },
    (Gender.FEMALE, "weight"): {
        0: LMS(l=0.3809, m=3.2322, s=0.14171),
        6: LMS(l=0.1714, m=7.2970, s=0.12204),
        12: LMS(l=0.0903, m=8.9481, s=0.11806),
        24: LMS(l=0.0186, m=11.4775, s=0.11691),
    },
    (Gender.FEMALE, "height"): {
        0: LMS(l=1.0, m=49.1477, s=0.03790),
        6: LMS(l=1.0, m=65.7311, s=0.03182),
        12: LMS(l=1.0, m=74.0148, s=0.03371),
        24: LMS(l=1.0, m=85.7153, s=0.03764),
    },
}

# Female tables double as the fallback for Gender.OTHER until a neutral
# reference is selected by the caller's clinical guidance.
_LMS_REFERENCE.update(
    {
        (Gender.OTHER, "weight"): _LMS_REFERENCE[(Gender.FEMALE, "weight")],
        (Gender.OTHER, "height"): _LMS_REFERENCE[(Gender.FEMALE, "height")],
    }
)


def _interpolate_lms(points: dict[int, LMS], age_months: float) -> LMS:
    """Linearly interpolate an ``LMS`` triple for an arbitrary age in months."""
    ages = sorted(points)
    if age_months <= ages[0]:
        return points[ages[0]]
    if age_months >= ages[-1]:
        return points[ages[-1]]

    # Find the bracketing anchor ages.
    lower = max(a for a in ages if a <= age_months)
    upper = min(a for a in ages if a >= age_months)
    if lower == upper:
        return points[lower]

    frac = (age_months - lower) / (upper - lower)
    lo, hi = points[lower], points[upper]
    return LMS(
        l=lo.l + (hi.l - lo.l) * frac,
        m=lo.m + (hi.m - lo.m) * frac,
        s=lo.s + (hi.s - lo.s) * frac,
    )


def _z_to_percentile(z: float) -> float:
    """Convert a z-score to a percentile (0–100) via the normal CDF."""
    cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return round(cdf * 100.0, 2)


def calculate_percentile(
    *,
    gender: Gender,
    metric: str,
    age_months: float,
    value: float,
) -> dict[str, float | str]:
    """Compute the WHO percentile for a single measurement.

    Args:
        gender: Infant gender (selects the reference chart).
        metric: ``"weight"`` (kg) or ``"height"`` (cm).
        age_months: Age in months (fractional allowed).
        value: The measured weight in kg, or height in cm.

    Returns:
        A dict with the z-score, percentile, the reference median, and a
        human-readable interpretation band.
    """
    metric = metric.lower()
    if metric not in {"weight", "height"}:
        raise ValueError("metric must be 'weight' or 'height'")

    points = _LMS_REFERENCE[(gender, metric)]
    lms = _interpolate_lms(points, age_months)

    # WHO LMS z-score formula.
    if lms.l == 0:
        z = math.log(value / lms.m) / lms.s
    else:
        z = (((value / lms.m) ** lms.l) - 1.0) / (lms.l * lms.s)

    percentile = _z_to_percentile(z)

    if percentile < 3:
        band = "below the 3rd percentile"
    elif percentile > 97:
        band = "above the 97th percentile"
    else:
        band = "within the typical range"

    return {
        "metric": metric,
        "z_score": round(z, 3),
        "percentile": percentile,
        "reference_median": round(lms.m, 2),
        "interpretation": band,
    }


# z-scores for the standard percentile boundaries used by the growth charts.
_PERCENTILE_Z: dict[int, float] = {
    5: -1.6448536269514722,
    50: 0.0,
    95: 1.6448536269514722,
}


def _value_for_z(lms: LMS, z: float) -> float:
    """Invert the WHO LMS formula to get the measurement value at a z-score."""
    if lms.l == 0:
        return lms.m * math.exp(lms.s * z)
    return lms.m * (1.0 + lms.l * lms.s * z) ** (1.0 / lms.l)


def reference_band(
    *,
    gender: Gender,
    metric: str,
    age_months: float,
) -> dict[int, float]:
    """Compute the 5th/50th/95th percentile *values* for a metric at an age.

    Returns ``{5: <value>, 50: <value>, 95: <value>}`` — the standard boundary
    measurements (kg for weight, cm for height) that bound a growth chart.
    """
    metric = metric.lower()
    if metric not in {"weight", "height"}:
        raise ValueError("metric must be 'weight' or 'height'")

    lms = _interpolate_lms(_LMS_REFERENCE[(gender, metric)], age_months)
    return {p: round(_value_for_z(lms, z), 2) for p, z in _PERCENTILE_Z.items()}
