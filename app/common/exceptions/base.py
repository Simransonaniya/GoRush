class AppError(Exception):
    """Base application exception. Never leak stack traces, internal
    service names, or raw DB errors to the client -- catch and re-map
    everything into one of these before it reaches the response layer."""

    code: str = "INTERNAL_ERROR"
    http_status: int = 500
    retryable: bool = False

    def __init__(self, message: str, *, code: str | None = None, http_status: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if http_status:
            self.http_status = http_status

    def to_dict(self, request_id: str) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "requestId": request_id,
            "retryable": self.retryable,
        }


class NotFoundError(AppError):
    code = "NOT_FOUND"
    http_status = 404


class UnauthorizedError(AppError):
    code = "UNAUTHORIZED"
    http_status = 401


class ForbiddenError(AppError):
    code = "FORBIDDEN"
    http_status = 403


class ValidationAppError(AppError):
    code = "VALIDATION_ERROR"
    http_status = 422


class RideNotFoundError(NotFoundError):
    code = "RIDE_NOT_FOUND"


class ToolDeniedError(ForbiddenError):
    code = "TOOL_DENIED"


class ConfirmationRequiredError(AppError):
    code = "CONFIRMATION_REQUIRED"
    http_status = 409


class UpstreamUnavailableError(AppError):
    code = "SERVICE_UNAVAILABLE"
    http_status = 503
    retryable = True


class RateLimitExceededError(AppError):
    code = "RATE_LIMITED"
    http_status = 429
    retryable = True


class NotEligibleError(AppError):
    """The resource exists but the requested action is not permitted by policy."""
    code = "NOT_ELIGIBLE"
    http_status = 422


class ConflictError(AppError):
    """The request conflicts with current state (e.g. ride already cancelled)."""
    code = "CONFLICT"
    http_status = 409


class DuplicateRequestError(AppError):
    """Idempotency key was already used for a different payload."""
    code = "DUPLICATE_REQUEST"
    http_status = 409


class ToolTimeoutError(AppError):
    """The upstream GoRush service did not respond in time."""
    code = "TOOL_TIMEOUT"
    http_status = 504
    retryable = True


class PromptInjectionDetectedError(ForbiddenError):
    code = "PROMPT_INJECTION_DETECTED"
