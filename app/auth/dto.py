from pydantic import BaseModel, Field

from app.common.enums.chat import UserRole


class LoginRequest(BaseModel):
    external_ref: str = Field(..., description="GoRush user identifier")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
