# Opportunity Atlas

Self-hosted opportunity intelligence engine for discovering, extracting, verifying, deduplicating, scoring and monitoring grants, bounties, prizes, hackathons, research calls, paid pilots and tenders.

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

Open `http://localhost:8000/docs` for the API and `http://localhost:3000` for the web application.

## Phases 1–3

- Phase 1: source registry, SearXNG/direct discovery, OpenAI-compatible structured extraction, verification, deduplication, PostgreSQL, campaigns and scheduler.
- Phase 2: multilingual query generation, recursive source discovery, query performance, historical records and source trust.
- Phase 3: user profiles, explainable matching, opportunity scoring, recurrence prediction, alerts/watchlists, dashboard and API.

LLM configuration is provider-independent through `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`.
