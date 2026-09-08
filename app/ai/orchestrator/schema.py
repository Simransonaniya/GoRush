from pydantic import BaseModel

from app.common.enums.chat import Intent, Language, Priority


class HandoffInfo(BaseModel):
    triggered: bool = False
    priority: Priority | None = None
    reason: str | None = None
    handoff_id: str | None = None


class OrchestrationResult(BaseModel):
    model_config = {"protected_namespaces": ()}  # allow llm_version without "model_" conflict

    message: str
    language: Language
    intent: Intent
    actions: list[str] = []  # names of tools that were executed
    handoff: HandoffInfo = HandoffInfo()
    llm_version: str   # renamed from model_version to avoid Pydantic v2 "model_" namespace warning
    prompt_version: str
