# GoRush AI Chatbot Backend (Python / FastAPI)

Production-oriented, modular, multilingual (English / Hindi / Hinglish) AI
support backend for GoRush. Implements: UNDERSTAND -> VERIFY -> ACT -> EXPLAIN -> ESCALATE.

## Stack
FastAPI, SQLAlchemy (async) + PostgreSQL + pgvector, Redis, JWT/RBAC,
provider-agnostic LLM gateway (Anthropic implementation included, with
primary -> fallback -> deterministic-response chain), WebSocket streaming,
Docker Compose, Alembic migrations, pytest.

## Architecture

Client -> API Gateway (FastAPI) -> Auth (JWT/RBAC) -> Chat Router
      -> Conversation/Context Service -> AI Orchestrator
      -> Guardrails (PII / prompt-injection) -> Intent + Language Detection
      -> RAG Retrieval (pgvector, approved knowledge only)
      -> Tool Router (allowlist -> role check -> ownership check ->
         confirmation gate -> idempotency -> execute -> audit)
      -> LLM Gateway (primary/fallback models)
      -> Output Guardrails -> Response
      -> Audit Log

The LLM never touches the database directly. All GoRush data access goes
through the Tool Registry -> Tool Router -> mock/real GoRush clients.

## Folder structure

app/
  core/            settings, logging
  common/          enums, exceptions, middleware
  database/        async SQLAlchemy session + mixins
  redis_cache/     redis client, rate limiter
  auth/            JWT, RBAC, login route
  users/           user model
  chat/            sessions/messages models, REST router, WS gateway, DTOs
  conversations/   persistence + context/summarization service
  ai/
    language/      en/hi/Hinglish detector
    intent/        rule-based fast-path intent detection
    llm/           provider interface, Anthropic impl, fallback gateway
    prompts/       versioned system prompts
    orchestrator/  the full message pipeline + loop guard
  guardrails/      PII redaction, prompt-injection detection, in/out pipelines
  tools/
    registry/      tool spec + central allowlist registry
    router/        enforced tool-execution security pipeline
    idempotency/   Redis-backed idempotency for high-risk actions
    ride/ payment/ support/ safety/   concrete tools + mock GoRush clients
  knowledge/       pgvector models + RAG retrieval service
  handoff/         human handoff summaries + models
  admin/           knowledge/prompt admin APIs (ADMIN role only)
  audit/           audit log model + service
  health/          liveness/readiness probes
  jobs/            background worker entrypoint
alembic/           DB migrations
tests/             unit / security / integration
scripts/           local dev helpers (seed data)
docker-compose.yml, Dockerfile, .env.example

## Running locally

cp .env.example .env        (fill in LLM_API_KEY)
docker compose up --build
docker compose exec api alembic upgrade head
docker compose exec api python -m scripts.seed_demo_user

API docs: http://localhost:8000/docs
Health: http://localhost:8000/healthz , /readyz

## Tests

pip install -r requirements.txt
pytest

## Important notes / what's mocked

- app/tools/ride/gorush_clients.py contains MOCK GoRush Ride/Payment/
  Support/Safety clients, clearly marked. Replace with real HTTP clients
  against GoRush's internal APIs (base URLs already read from env config)
  when those are available.
- AnthropicProvider.embeddings() is an explicit NotImplementedError seam --
  plug in an embeddings provider (e.g. Voyage AI) before RAG can retrieve
  real results; the orchestrator degrades gracefully if it's not configured.
- Never hardcode API keys -- everything comes from .env / environment.
