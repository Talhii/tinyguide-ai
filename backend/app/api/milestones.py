"""Milestones router.

Returns age-banded developmental milestones and accepts milestone check-offs.
Phase 1 serves a static reference set; persistence is stubbed.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/milestones", tags=["milestones"])


class Milestone(BaseModel):
    """A single developmental milestone."""

    id: str
    title: str
    category: str = Field(..., description="e.g. motor, social, language, cognitive.")
    typical_age_months: int = Field(..., ge=0, le=60)
    description: str = Field("", description="What this milestone looks like.")
    tips: list[str] = Field(default_factory=list, description="Ways to support it.")


# Illustrative reference set. Replace with a curated, sourced dataset.
_MILESTONES: list[Milestone] = [
    Milestone(
        id="m1",
        title="Lifts head during tummy time",
        category="motor",
        typical_age_months=2,
        description=(
            "While lying on their tummy, your baby briefly lifts their head and "
            "turns it to the side. This builds the neck and shoulder strength "
            "needed for rolling, sitting, and crawling later on."
        ),
        tips=[
            "Do short tummy-time sessions a few times a day while baby is awake.",
            "Get down to their level and use a toy or your face to encourage looking up.",
        ],
    ),
    Milestone(
        id="m2",
        title="Smiles responsively",
        category="social",
        typical_age_months=2,
        description=(
            "Your baby smiles back when you smile or talk to them — a 'social "
            "smile' rather than a reflex. It's one of the first signs of "
            "two-way connection."
        ),
        tips=[
            "Make eye contact, smile, and talk in a warm, sing-song voice.",
            "Pause after you speak to give baby a turn to respond.",
        ],
    ),
    Milestone(
        id="m3",
        title="Coos and babbles",
        category="language",
        typical_age_months=4,
        description=(
            "Baby starts making vowel sounds ('ooh', 'aah') and later strings of "
            "babble ('ba-ba', 'da-da'). This is early speech practice."
        ),
        tips=[
            "Repeat the sounds your baby makes back to them — it's a conversation.",
            "Narrate your day and name objects to grow their word bank.",
        ],
    ),
    Milestone(
        id="m4",
        title="Sits without support",
        category="motor",
        typical_age_months=6,
        description=(
            "Your baby can sit upright on their own for a little while without "
            "you holding them, freeing their hands to explore and play."
        ),
        tips=[
            "Surround them with cushions at first so tumbles are soft.",
            "Place toys just within reach to encourage balance and reaching.",
        ],
    ),
    Milestone(
        id="m5",
        title="Responds to own name",
        category="social",
        typical_age_months=7,
        description=(
            "When you say their name, your baby turns to look or reacts. It "
            "shows growing awareness of themselves and of language."
        ),
        tips=[
            "Use their name often in everyday talk and during play.",
            "Say their name from different spots in the room and wait for them to find you.",
        ],
    ),
    Milestone(
        id="m6",
        title="Pulls to stand",
        category="motor",
        typical_age_months=9,
        description=(
            "Baby grabs furniture or your hands and pulls themselves up to "
            "standing — a big step toward cruising and walking."
        ),
        tips=[
            "Make sure furniture is stable and anchor anything that could tip.",
            "Let them practice on a low, sturdy surface with you close by.",
        ],
    ),
    Milestone(
        id="m7",
        title="Says first words",
        category="language",
        typical_age_months=12,
        description=(
            "Your baby says one or two meaningful words like 'mama', 'dada', or "
            "'bye' and starts linking words to people and things."
        ),
        tips=[
            "Read picture books together every day and name what you see.",
            "Respond to attempts warmly, even if the word isn't perfect yet.",
        ],
    ),
    Milestone(
        id="m8",
        title="Walks independently",
        category="motor",
        typical_age_months=12,
        description=(
            "Baby takes their first steps on their own. The normal range is "
            "wide — many children walk anywhere from 9 to 18 months."
        ),
        tips=[
            "Give them safe, open floor space and let them go barefoot indoors for grip.",
            "Cheer their attempts; avoid walkers, which can delay independent walking.",
        ],
    ),
]


@router.get("", response_model=list[Milestone])
async def list_milestones(
    max_age_months: int | None = Query(None, ge=0, le=60, description="Filter to this age or younger."),
) -> list[Milestone]:
    """List developmental milestones, optionally capped by age."""
    if max_age_months is None:
        return _MILESTONES
    return [m for m in _MILESTONES if m.typical_age_months <= max_age_months]
