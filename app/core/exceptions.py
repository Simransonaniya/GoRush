"""
Global exception handlers.

Spec ref: section 29 -- never expose stack traces, internal service
names, or raw database errors to the client. Every error response uses
the same shape: { code, message, requestId, retryable }.
"""

import logging

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger("gorush")


def _error_body(request: Request, code: str, message: str, retryable: bool = False) -> dict:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "requestId": getattr(request.state, "request_id", None),
            "retryable": retryable,
        },
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(request, code=f"HTTP_{exc.status_code}", message=str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        # Log the real exception internally, but never leak it to the client.
        logger.exception("Unhandled exception", extra={"request_id": getattr(request.state, "request_id", None)})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                request,
                code="INTERNAL_ERROR",
                message="Something went wrong. Please try again.",
                retryable=True,
            ),
        )
