"""
Auth service.

Spec ref section 43: "Do not put business logic into controllers."
Routes stay thin (parse request -> call service -> return response);
all the actual logic lives here so it's testable in isolation from HTTP.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, req: RegisterRequest) -> User:
        existing = await self.db.execute(select(User).where(User.phone == req.phone))
        if existing.scalar_one_or_none():
            raise HTTPException(status.HTTP_409_CONFLICT, "Phone number already registered")

        user = User(
            phone=req.phone,
            email=req.email,
            hashed_password=hash_password(req.password),
            role=req.role,
            preferred_language=req.preferred_language,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def login(self, req: LoginRequest) -> str:
        result = await self.db.execute(select(User).where(User.phone == req.phone))
        user = result.scalar_one_or_none()
        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid phone or password")
        if not user.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")

        return create_access_token(subject=str(user.id), role=user.role.value)
