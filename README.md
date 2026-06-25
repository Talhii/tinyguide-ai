# TinyGuide AI — AI-Powered Mobile Parenting Companion 🍼

> A premium, mobile-first companion for new parents: track growth against WHO
> percentile curves, follow a birthday-relative vaccination plan, check
> developmental milestones, and ask an emergency-aware AI assistant grounded in
> a local pediatric knowledge base.

TinyGuide AI is a **dual-service monorepo**: a Python **FastAPI** microservice
and a **Next.js 14** web app, developed and deployed independently.

```
TinyGuide-AI/
├── frontend/   # Next.js 14 (App Router) · TypeScript · Tailwind · shadcn/ui  → :3000
└── backend/    # Python 3.11+ · FastAPI microservice                          → :8000
```

---

## Service topology

| Service | Stack | Port | Responsibility |
|---------|-------|------|----------------|
| **Frontend** (`/frontend`) | Next.js 14 App Router, TypeScript, Tailwind, shadcn/ui, Recharts | `3000` | Mobile-first UI, floating nav, growth charts, typed fetch hooks |
| **Backend** (`/backend`) | FastAPI, Pydantic v2, LangChain + Anthropic SDK, Supabase | `8000` | REST API, WHO LMS math, triage guardrail, RAG knowledge base |

The frontend calls the backend over HTTP (`NEXT_PUBLIC_API_URL`, default
`http://localhost:8000`). The backend enables CORS for the `:3000` dev server.

---

## Headline capabilities

### 📈 WHO LMS growth percentiles
Growth analytics use the WHO **LMS method** (`L` = Box-Cox power, `M` = median,
`S` = coefficient of variation). The engine converts a raw weight/height into a
z-score and percentile, and inverts the same formula to produce the 5th / 50th /
95th percentile **boundary values** at any age — so the chart's shaded band bends
with the child's age. Reference points are interpolated per age in
[`services/percentile.py`](backend/app/services/percentile.py).

> The shipped reference table is illustrative; drop in the full WHO Child Growth
> Standards tables for production accuracy — the public function signatures stay
> the same.

### 🚨 Regex triage medical guardrail
Before any model call, the AI orchestrator runs a **word-boundary regex** over
high-risk medical keywords (`fever`, `choking`, `seizure`, `poison`,
`swallowed`, …). On a hit it injects a `SAFETY OVERRIDE` directive forcing the
model to prepend a clinical warning, and the API returns `is_emergency: true`
plus `recommended_actions` (Call 911 / pediatrician / Poison Control). See
[`services/ai_orchestrator.py`](backend/app/services/ai_orchestrator.py).

### 💉 Birthday-relative vaccine tracker
`GET /api/vaccinations/{infant_id}` computes each milestone dose's due date from
the infant's `birth_date` (calendar-accurate month math) and buckets it as
`OVERDUE` / `UPCOMING` / `SAFE`. Doses already present in the administered log
are synced to `COMPLETED`.

### 🧠 Local-first knowledge & memory strategy
The assistant is **local-first**: a static pediatric knowledge base
([`api/rag.py`](backend/app/api/rag.py)) is searched with a keyword gate
(`sleep`, `smile`, `milestone`, `solid food`, …). Matched reference text is
injected into the orchestrator so answers stay grounded, and the source document
titles are returned as a `citations` array. Growth measurements are held in an
in-memory store (`_GROWTH_LOGS`) for instant, zero-dependency local development;
both the knowledge base and the store are designed to swap to Supabase /
pgvector without changing the API contracts.

### 🌱 Live growth logging + Composed Area chart
Parents log measurements via `POST /api/analytics/growth-log`; the dashboard's
Recharts `ComposedChart` renders the child's terracotta trajectory over a shaded
5th–95th percentile **area band** with a dashed median. Logging a measurement
refetches the timeline so the chart updates in real time.

---

## Backend layout

```
backend/
├── main.py                  # FastAPI entry point (async, port 8000, CORS)
├── requirements.txt
└── app/
    ├── api/                 # Routers
    │   ├── infants.py         # Pydantic-validated infant registration
    │   ├── analytics.py       # growth-percentile · growth-log · growth-timeline
    │   ├── milestones.py
    │   ├── dashboard.py       # Dashboard log inputs
    │   ├── vaccinations.py    # Schedule · logs · birthday-relative tracker
    │   └── rag.py             # AI assistant + local knowledge base
    ├── services/
    │   ├── percentile.py      # WHO LMS percentile + band math
    │   └── ai_orchestrator.py # Triage guardrail + RAG generation (Claude)
    └── core/
        ├── config.py          # Env var wrapper (pydantic-settings)
        ├── database.py        # Supabase client config
        └── security.py        # Shared schemas / enums
```

### Key endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/infants` | Register an infant (`name`, `birth_date`, `gender`) |
| `POST` | `/api/analytics/growth-percentile` | WHO percentile for a single measurement |
| `POST` | `/api/analytics/growth-log` | Log a weight/height measurement |
| `POST` | `/api/analytics/growth-timeline` | Timeline of logged points vs WHO bands |
| `GET`  | `/api/vaccinations/{infant_id}` | Birthday-relative dose plan w/ statuses |
| `GET`  | `/api/milestones` | Developmental milestones |
| `POST` | `/api/assistant/ask` | Emergency-aware, citation-grounded Q&A |

Interactive API docs: **http://localhost:8000/docs**

---

## Running both services concurrently

Open **two terminals**.

### 1 · Backend (port 8000)

```bash
cd backend
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # keys optional for local dev
uvicorn main:app --reload --port 8000
```

### 2 · Frontend (port 3000)

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

App: **http://localhost:3000**

---

## Local-first by design

Everything runs with **no external keys**:

- **Supabase** optional — routers use in-memory stores until configured.
- **Anthropic / Claude** optional — the assistant returns a clearly labelled
  stub (still emergency-aware and citation-grounded) until `ANTHROPIC_API_KEY`
  is set. When configured, generation uses `claude-opus-4-8` via the official
  Anthropic SDK; LangChain powers the retrieval layer.
- **Growth measurements** live in an in-memory store — they reset on backend
  restart until persistence is wired to Supabase.

This makes the whole product clonable and demoable end-to-end in minutes, with a
clean upgrade path to managed persistence and live AI.
