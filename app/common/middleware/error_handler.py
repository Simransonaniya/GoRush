import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.common.exceptions.base import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.warning("app_error", code=exc.code, message=exc.message, request_id=request_id)
        return JSONResponse(
            status_code=exc.http_status,
            content={"success": False, "error": exc.to_dict(request_id)},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
        logger.error("unhandled_exception", error=str(exc), request_id=request_id)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Something went wrong. Please try again.",
                    "requestId": request_id,
                    "retryable": True,
                },
            },
        )
