"""
Auth dependencies.

Why this exists:
NestJS uses Guards (`@UseGuards(JwtAuthGuard, RolesGuard)`) attached to
routes. FastAPI's equivalent is `Depends(...)`: a function that runs
before the route handler and either returns data (the current user) or
raises an HTTPException, which stops the request. `require_roles(...)`
below is our RolesGuard equivalent -- pass it the allowed roles and it
becomes a reusable dependency.
"""

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None or "sub" not in payload:
        raise credentials_error

    user_id = uuid.UUID(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_roles(*allowed_roles: UserRole):
    """
    Usage: Depends(require_roles(UserRole.ADMIN, UserRole.SUPPORT_AGENT))
    Equivalent to NestJS's @Roles(...) decorator + RolesGuard combo.
    """

    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _check
