"""
Request ID middleware.

Spec ref: section 29 (structured errors include requestId), section 30
(observability -- trace every request). Every request gets a UUID,
exposed on `request.state.request_id` and echoed back in the
`X-Request-ID` response header, so a user-reported bug can be traced
through logs end to end.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
