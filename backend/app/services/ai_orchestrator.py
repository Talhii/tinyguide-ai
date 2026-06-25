"""AI orchestrator for the parenting assistant (RAG) with a triage guardrail.

Responsibilities:
  * **Triage** the caregiver's query for high-risk medical language before any
    generation happens (the emergency guardrail).
  * Retrieve relevant parenting/medical context (RAG) — backed by
    ``langchain-community`` document loaders + vector stores in production.
  * Generate the final answer with Claude via the **official Anthropic SDK**.

Phase 1 ships a working orchestrator that gracefully degrades: if no
``ANTHROPIC_API_KEY`` is configured it returns a clearly-labelled stub answer
(still emergency-aware), so the frontend chat flow is testable end-to-end before
keys are wired in.
"""

from __future__ import annotations

import re

from app.core.config import settings

# System prompt that anchors the assistant's persona and safety posture.
_SYSTEM_PROMPT = (
    "You are TinyGuide, a warm, evidence-based AI parenting companion. "
    "You help caregivers with infant milestones, growth, feeding, sleep, and "
    "vaccinations. Be reassuring and concise. You are not a substitute for "
    "professional medical advice — recommend contacting a pediatrician for "
    "anything urgent or concerning."
)

# Standard clinical warning prepended to any emergency-flagged answer.
_CLINICAL_WARNING = (
    "⚠️ This may be a medical emergency. This information is not a "
    "substitute for professional medical care. If your child is in distress, "
    "call your local emergency number (911 in the US) or contact your "
    "pediatrician immediately."
)

# Systemic instruction injected into Claude's context when triage fires. It
# forces the model to lead with an emergency warning (in the reply's language).
_EMERGENCY_DIRECTIVE = (
    "SAFETY OVERRIDE: The caregiver's message may describe a medical emergency. "
    "Begin your reply with a clear, prominent warning that this may be an "
    "emergency and that they should seek immediate professional medical help — "
    "written in the same language as the rest of your reply. Then give brief, "
    "calm, first-step guidance. Do not downplay the situation."
)

# How the assistant should phrase its answer, by selected language.
_LANGUAGE_INSTRUCTION: dict[str, str] = {
    "en": "Respond in clear, simple English.",
    "ur": (
        "Respond in Urdu using Urdu (اردو) script. Use warm, simple, everyday "
        "Urdu that any parent can easily understand."
    ),
    "roman": (
        "Respond in Roman Urdu — Urdu written using English/Latin letters, the "
        "way people chat casually (e.g. 'aap ke baby ko...'). Keep it warm and "
        "simple. Do not use Urdu script."
    ),
}

# High-risk medical keywords that trigger the triage guardrail. Single words
# match on word boundaries; multi-word phrases match as phrases.
_EMERGENCY_KEYWORDS: tuple[str, ...] = (
    "fever",
    "choking",
    "choke",
    "unresponsive",
    "seizure",
    "seizing",
    "convulsion",
    "convulsing",
    "poison",
    "poisoned",
    "poisoning",
    "swallowed",
    "swallow",
    "not breathing",
    "stopped breathing",
    "can't breathe",
    "cant breathe",
    "difficulty breathing",
    "turning blue",
    "blue lips",
    "won't wake",
    "wont wake",
    "limp",
    "anaphylaxis",
    "allergic reaction",
)

_EMERGENCY_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _EMERGENCY_KEYWORDS) + r")\b",
    re.IGNORECASE,
)

# Base actions surfaced to the caregiver on any emergency.
_BASE_ACTIONS: tuple[str, ...] = (
    "Call 911 (or your local emergency number)",
    "Contact your pediatrician immediately",
    "Keep your child calm and monitor their breathing",
)

# Ingestion-related keywords get an extra Poison Control action.
_POISON_KEYWORDS = {"poison", "poisoned", "poisoning", "swallowed", "swallow"}


def _triage(query: str) -> tuple[bool, list[str]]:
    """Classify a query for medical emergencies.

    Returns ``(is_emergency, recommended_actions)``. When no high-risk keyword
    is present, returns ``(False, [])``.
    """
    matches = {m.group(0).lower() for m in _EMERGENCY_RE.finditer(query)}
    if not matches:
        return False, []

    actions = list(_BASE_ACTIONS)
    if matches & _POISON_KEYWORDS:
        actions.append("Call Poison Control (US: 1-800-222-1222)")
    return True, actions


def _retrieve_context(query: str) -> list[str]:
    """Placeholder RAG retrieval.

    Replace with a ``langchain-community`` retriever (e.g. a Supabase/pgvector
    or FAISS vector store) that returns the top-k relevant document chunks for
    ``query``. Returning an empty list simply means "no extra context".
    """
    # TODO(rag): wire up vector store retrieval over the parenting corpus.
    return []


async def answer_question(
    query: str,
    context: list[str] | None = None,
    history: list[dict[str, str]] | None = None,
    language: str = "en",
) -> dict[str, object]:
    """Answer a caregiver question, augmented with retrieved context.

    Runs the triage guardrail first, then generates an answer. Callers may pass
    pre-retrieved ``context`` chunks (e.g. from the local knowledge base in the
    RAG router) and the prior conversation ``history`` (a list of
    ``{"role", "content"}`` turns) so follow-up questions keep their context.
    The returned dict always includes ``is_emergency`` and
    ``recommended_actions`` so the frontend can render the emergency UI
    deterministically.
    """
    is_emergency, recommended_actions = _triage(query)
    sources = context if context is not None else _retrieve_context(query)

    # Build the prompt once — only the provider call differs below.
    system = _SYSTEM_PROMPT
    if is_emergency:
        system = f"{system}\n\n{_EMERGENCY_DIRECTIVE}"
    system = f"{system}\n\n{_LANGUAGE_INSTRUCTION.get(language, _LANGUAGE_INSTRUCTION['en'])}"

    context_block = ""
    if sources:
        joined = "\n\n".join(f"- {chunk}" for chunk in sources)
        context_block = f"\n\nRelevant reference material:\n{joined}"
    user_content = f"{query}{context_block}"

    # Conversation: prior turns + this turn, so follow-ups have context.
    chat_messages = _normalize_history(history)
    chat_messages.append({"role": "user", "content": user_content})

    # Provider priority: Groq (free) → Claude → a labelled offline stub.
    if settings.groq_api_key:
        answer, model = await _generate_groq(system, chat_messages)
    elif settings.anthropic_api_key:
        answer, model = await _generate_claude(system, chat_messages)
    else:
        prefix = f"{_CLINICAL_WARNING}\n\n" if is_emergency else ""
        answer = (
            f"{prefix}[stub] TinyGuide's AI assistant is not yet connected. "
            "Add a free GROQ_API_KEY (or ANTHROPIC_API_KEY) in the backend "
            f"environment to enable live answers. You asked: {query!r}"
        )
        model = "stub"

    return {
        "answer": answer,
        "sources": sources,
        "model": model,
        "is_emergency": is_emergency,
        "recommended_actions": recommended_actions,
    }


# Keep only the most recent turns so long chats stay cheap and in-context.
_MAX_HISTORY_TURNS = 20


def _normalize_history(
    history: list[dict[str, str]] | None,
) -> list[dict[str, str]]:
    """Clean caller-supplied history into a valid, alternating message list."""
    if not history:
        return []

    cleaned = [
        {"role": m["role"], "content": m["content"]}
        for m in history
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    cleaned = cleaned[-_MAX_HISTORY_TURNS:]

    # Conversations must begin with a user turn (required by Claude; harmless
    # for Groq) — drop any leading assistant turns left over after trimming.
    while cleaned and cleaned[0]["role"] != "user":
        cleaned.pop(0)
    return cleaned


async def _generate_groq(
    system: str,
    messages: list[dict[str, str]],
) -> tuple[str, str]:
    """Generate an answer with Groq (free, OpenAI-compatible chat API)."""
    # Imported lazily so the package stays optional until a key is set.
    from groq import AsyncGroq

    client = AsyncGroq(api_key=settings.groq_api_key)
    resp = await client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=1024,
        messages=[{"role": "system", "content": system}, *messages],
    )
    return (resp.choices[0].message.content or ""), resp.model


async def _generate_claude(
    system: str,
    messages: list[dict[str, str]],
) -> tuple[str, str]:
    """Generate an answer with Claude via the official Anthropic SDK."""
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    message = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    answer = next(
        (block.text for block in message.content if block.type == "text"),
        "",
    )
    return answer, message.model
