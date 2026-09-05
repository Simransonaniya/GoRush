from pydantic import BaseModel

from app.common.enums.chat import Intent, Language, Priority


class HandoffInfo(BaseModel):
    triggered: bool = False
    priority: Priority | None = None
    reason: str | None = None
    handoff_id: str | None = None


class OrchestrationResult(BaseModel):
    message: str
    language: Language
    intent: Intent
    actions: list[str] = []  # names of tools that were executed
    handoff: HandoffInfo = HandoffInfo()
    model_version: str
    prompt_version: str
