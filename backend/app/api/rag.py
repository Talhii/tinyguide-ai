"""RAG query router with a local-first pediatric knowledge base.

Front door to the AI parenting assistant. When a query touches developmental or
routine-care topics, the router searches a small static knowledge base, feeds
the matched reference text into the AI orchestrator so Claude grounds its answer
in it, and returns the source document titles as ``citations``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.ai_orchestrator import answer_question

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


# ---------------------------------------------------------------------------
# Local knowledge base (ingestion layer)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class KnowledgeDoc:
    """A single static pediatric reference document."""

    title: str
    content: str
    keywords: tuple[str, ...]


# Static reference corpus. Replace/extend with a vector store for richer recall;
# the matching contract (title + content) stays the same.
_KNOWLEDGE_BASE: tuple[KnowledgeDoc, ...] = (
    KnowledgeDoc(
        title="AAP Safe Sleep Guidelines",
        content=(
            "Infants should always be placed on their backs to sleep, for naps "
            "and at night, to reduce the risk of SIDS. Use a firm, flat sleep "
            "surface in a crib or bassinet with no pillows, blankets, bumpers, "
            "or soft toys. Room-share without bed-sharing for the first 6–12 "
            "months."
        ),
        keywords=("sleep", "sleeping", "nap", "naps", "sids", "bedtime", "crib", "bassinet"),
    ),
    KnowledgeDoc(
        title="Developmental Milestones Overview",
        content=(
            "Social smiles typically emerge around 2 months. Babies often roll "
            "over by 4–6 months, sit unsupported by about 6 months, and may take "
            "first steps around 12 months. Milestones are guides, not deadlines "
            "— ranges are wide and vary by child."
        ),
        keywords=("milestone", "milestones", "smile", "smiles", "smiling", "roll", "crawl", "walk", "develop", "development"),
    ),
    KnowledgeDoc(
        title="Introducing Solid Foods",
        content=(
            "Most babies are ready for solid food around 6 months, once they can "
            "sit with support and show interest in food. Start with single-"
            "ingredient purees or soft finger foods and introduce new foods one "
            "at a time, a few days apart, to watch for allergies."
        ),
        keywords=("solid food", "solid foods", "solids", "puree", "purees", "weaning", "feeding", "eat", "eating"),
    ),
    KnowledgeDoc(
        title="Tummy Time Basics",
        content=(
            "Supervised tummy time while awake helps build neck, shoulder, and "
            "core strength and supports motor milestones. Start with a few "
            "minutes several times a day and build up as your baby grows."
        ),
        keywords=("tummy time", "tummy", "motor", "head control", "neck"),
    ),
)

# The keyword gate: any of these (the union of all doc keywords) routes a query
# through the local knowledge search before generation.
_ROUTINE_KEYWORDS: frozenset[str] = frozenset(
    kw for doc in _KNOWLEDGE_BASE for kw in doc.keywords
)


def _hits_routine_keyword(query: str) -> bool:
    """True when the query mentions any developmental / routine-care keyword."""
    q = query.lower()
    return any(re.search(rf"\b{re.escape(kw)}\b", q) for kw in _ROUTINE_KEYWORDS)


def _search_knowledge(query: str) -> list[KnowledgeDoc]:
    """Search the knowledge base, but only when the routine-keyword gate fires."""
    if not _hits_routine_keyword(query):
        return []

    q = query.lower()
    matched: list[KnowledgeDoc] = []
    for doc in _KNOWLEDGE_BASE:
        if any(re.search(rf"\b{re.escape(kw)}\b", q) for kw in doc.keywords):
            matched.append(doc)
    return matched


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    """A single prior turn in the conversation."""

    role: Literal["user", "assistant"]
    content: str


class AssistantQuery(BaseModel):
    """A caregiver question for the AI assistant, with optional chat history."""

    query: str = Field(..., min_length=1, max_length=2000, examples=["When should my baby start crawling?"])
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Prior conversation turns, oldest first, for follow-up context.",
    )
    language: Literal["en", "ur", "roman"] = Field(
        "en", description="Answer language: English, Urdu script, or Roman Urdu."
    )


class AssistantResponse(BaseModel):
    """The assistant's answer plus provenance, citations, and triage signals."""

    answer: str
    sources: list[str]
    citations: list[str] = Field(
        default_factory=list,
        description="Titles of knowledge-base documents used to ground the answer.",
    )
    model: str
    is_emergency: bool = Field(
        False,
        description="True when the triage guardrail detected high-risk medical language.",
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Emergency next steps to surface to the caregiver.",
    )


@router.post("/ask", response_model=AssistantResponse)
async def ask_assistant(payload: AssistantQuery) -> AssistantResponse:
    """Answer a parenting question using local-first retrieval-augmented generation."""
    docs = _search_knowledge(payload.query)
    context = [f"{doc.title}: {doc.content}" for doc in docs]
    citations = [doc.title for doc in docs]

    # Pass matched reference text + prior turns into the orchestrator so the
    # model grounds its answer and remembers the conversation.
    result = await answer_question(
        payload.query,
        context=context,
        history=[turn.model_dump() for turn in payload.history],
        language=payload.language,
    )

    return AssistantResponse(**result, citations=citations)
