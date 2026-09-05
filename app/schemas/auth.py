"""
Auth DTOs (Pydantic = NestJS's class-validator DTOs).

Pydantic validates types/shapes automatically at the FastAPI route
boundary -- if a request body doesn't match, FastAPI returns a 422
with details, before your code ever runs. Same job as Nest's
ValidationPipe + DTO classes.
"""

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    phone: str = Field(min_length=6, max_length=20)
    email: EmailStr | None = None
    password: str = Field(min_length=8)
    role: UserRole = UserRole.CUSTOMER
    preferred_language: str = "en"


class LoginRequest(BaseModel):
    phone: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    phone: str
    email: str | None
    role: UserRole
    preferred_language: str

    model_config = {"from_attributes": True}
