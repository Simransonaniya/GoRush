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
