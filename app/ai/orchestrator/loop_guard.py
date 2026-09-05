from app.common.exceptions.base import AppError


class OrchestrationLimitExceededError(AppError):
    code = "ORCHESTRATION_LIMIT_EXCEEDED"
    http_status = 200  # not a client error; caller should fall back gracefully
    retryable = False


class LoopGuard:
    """Bounds tool-call and orchestration-step counts per conversational
    turn to prevent LLM<->tool infinite loops."""

    def __init__(self, max_tool_calls: int, max_steps: int):
        self.max_tool_calls = max_tool_calls
        self.max_steps = max_steps
        self.tool_call_count = 0
        self.step_count = 0

    def record_step(self) -> None:
        self.step_count += 1
        if self.step_count > self.max_steps:
            raise OrchestrationLimitExceededError("Max orchestration steps exceeded for this turn")

    def record_tool_call(self) -> None:
        self.tool_call_count += 1
        if self.tool_call_count > self.max_tool_calls:
            raise OrchestrationLimitExceededError("Max tool calls exceeded for this turn")
