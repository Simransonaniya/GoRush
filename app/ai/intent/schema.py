from pydantic import BaseModel, Field

from app.common.enums.chat import Intent, Language, Priority, RiskLevel


class IntentResult(BaseModel):
    intent: Intent
    confidence: float = Field(ge=0.0, le=1.0)
    entities: dict = Field(default_factory=dict)
    urgency: Priority
    sentiment: str = "neutral"
    language: Language
    script: str = "latin"  # latin | devanagari | mixed
    requires_tool: bool = False
    requires_human: bool = False
    risk_level: RiskLevel = RiskLevel.LOW
