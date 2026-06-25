# TinyGuide AI — Backend

FastAPI microservice. Python 3.11+. Serves the REST API on **port 8000**.

## Setup

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Run

```bash
uvicorn main:app --reload --port 8000
# or
python main.py
```

- Swagger UI: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/infants` | Register an infant (`name`, `birth_date`, `gender`) |
| `GET`  | `/api/infants` | List infants |
| `POST` | `/api/analytics/growth-percentile` | WHO percentile for weight/height |
| `GET`  | `/api/milestones` | Developmental milestones (`?max_age_months=`) |
| `POST` | `/api/dashboard/entries` | Log a sleep/feeding/mood entry |
| `GET`  | `/api/vaccinations/schedule` | Recommended vaccine schedule |
| `POST` | `/api/vaccinations/logs` | Record an administered vaccine |
| `POST` | `/api/assistant/ask` | Ask the AI assistant (RAG) |

## Configuration

All config flows through `app/core/config.py` (env + `.env`). See
`.env.example`. Supabase and Anthropic keys are **optional** in Phase 1 — the
service boots and the routes work without them (in-memory store + stubbed AI).

## Notes

- The WHO percentile logic in `app/services/percentile.py` ships with a small
  **placeholder** LMS reference table. Replace it with the official WHO Child
  Growth Standards tables for production accuracy.
- The AI orchestrator (`app/services/ai_orchestrator.py`) uses
  `langchain-community` for RAG retrieval and the official Anthropic SDK
  (`claude-opus-4-8`) for generation.
