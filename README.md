<<<<<<< HEAD
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
=======
# GoRush AI Chatbot Backend — Phase 1

Python/FastAPI implementation of the GoRush chatbot backend spec.
This is **Phase 1**: project setup, auth, chat sessions/messages,
Postgres, Redis, a mock LLM gateway, and health checks. Later phases
add intent/language detection, tool calling, RAG, guardrails, safety,
and human handoff.

## Stack (Python equivalents of the original NestJS spec)

| Spec asked for | We use |
|---|---|
| NestJS | FastAPI |
| TypeORM/Prisma | SQLAlchemy (async) + Alembic |
| class-validator DTOs | Pydantic schemas |
| Guards | `Depends()` |
| BullMQ | (added in a later phase) Celery/RQ |

## Running it in VS Code

### 1. Clone / open the folder
Open the `gorush-backend` folder in VS Code.

### 2. Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
In VS Code: `Cmd/Ctrl+Shift+P` → "Python: Select Interpreter" → pick `.venv`.

### 3. Start Postgres + Redis
Easiest: use Docker for just the infra, run the API locally for hot-reload + debugging.
```bash
docker compose up -d postgres redis
```
(Or install Postgres 16 + Redis natively if you prefer no Docker at all.)

### 4. Configure environment
```bash
cp .env.example .env
```
Leave `LLM_PROVIDER=mock` for now — no API key needed to run everything end to end.

### 5. Run database migrations
```bash
alembic revision --autogenerate -m "init users and chat tables"
alembic upgrade head
```

### 6. Run the API
```bash
uvicorn app.main:app --reload
```
Open http://localhost:8000/docs — FastAPI's auto-generated Swagger UI.
This is the fastest way to explore and test every endpoint by hand.

### 7. Try it
1. `POST /v1/auth/register` — create a user
2. `POST /v1/auth/login` — get a JWT (`access_token`)
3. Click "Authorize" in `/docs`, paste the token
4. `POST /v1/chat/sessions` — create a session
5. `POST /v1/chat/messages` — send a message, get a mock reply back
6. `GET /v1/health/deep` — confirm Postgres + Redis are actually reachable

## Full project (all phases) with Docker
```bash
docker compose up --build
```

## What's intentionally NOT here yet
- Intent/language/sentiment detection (Phase 2)
- Tool calling / tool registry (Phase 2)
- RAG / pgvector knowledge base (Phase 3)
- Guardrails: PII redaction, prompt-injection detection (Phase 3)
- Payments, refunds, cancellation, rematch tools (Phase 4)
- Safety escalation, human handoff, admin (Phase 5)
- WebSocket streaming, evaluation framework, load tests (Phase 6)

We build these next, one phase at a time.
>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd
