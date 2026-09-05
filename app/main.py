<<<<<<< HEAD
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.admin.router import router as admin_router
from app.auth.router import router as auth_router
from app.chat.gateway import router as chat_ws_router
from app.chat.router import router as chat_router
from app.chat.tools_router import router as chat_tools_router
from app.common.middleware.error_handler import register_exception_handlers
from app.common.middleware.request_id import RequestIdMiddleware
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.health.router import router as health_router

configure_logging()
logger = get_logger(__name__)
settings = get_settings()

app = FastAPI(
    title="GoRush AI Chatbot Backend",
    version=settings.api_version,
    description="Multilingual, tool-using, RAG-enabled AI support backend for GoRush.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "development" else [],
=======
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
>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
<<<<<<< HEAD
app.add_middleware(RequestIdMiddleware)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(chat_tools_router)
app.include_router(chat_ws_router)
app.include_router(admin_router)


@app.on_event("startup")
async def on_startup():
    logger.info("app_startup", env=settings.app_env, version=settings.api_version)
=======

# --- Global error handling ---
register_exception_handlers(app)

# --- Routers (each is one "module" in NestJS terms) ---
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
async def root():
    return {"service": settings.APP_NAME, "status": "running", "docs": "/docs"}
>>>>>>> 443cf3b4165506c1ab3de92f7a0272091d790bfd
