"""
Application entrypoint.

This is the equivalent of NestJS's `app.module.ts` (wiring) +
`main.ts` (bootstrap) combined. It:
  1. Creates the FastAPI app
  2. Registers middleware (CORS, request-id)
  3. Registers global exception handlers
  4. Mounts each feature's router under /v1/...

Run locally with:  uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth, chat, health
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.middleware import RequestIdMiddleware

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    debug=settings.DEBUG,
)

# --- Middleware ---
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENV == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global error handling ---
register_exception_handlers(app)

# --- Routers (each is one "module" in NestJS terms) ---
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {"service": settings.APP_NAME, "status": "running", "docs": "/docs"}
