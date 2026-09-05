import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.security import decode_access_token
from app.common.enums.chat import UserRole
from app.common.exceptions.base import ForbiddenError, UnauthorizedError
from app.database.session import get_db
from app.users.models import User

bearer_scheme = HTTPBearer(auto_error=False)


class AuthContext:
    def __init__(self, user: User):
        self.user = user
        self.user_id: uuid.UUID = user.id
        self.role: UserRole = UserRole(user.role)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")

    payload = decode_access_token(credentials.credentials)
    user_id = payload.get("sub")
    if not user_id:
        raise UnauthorizedError("Invalid token payload")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id), User.is_active.is_(True)))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError("User not found or inactive")

    return AuthContext(user)


def require_roles(*allowed_roles: UserRole):
    """RBAC guard: use as a FastAPI dependency on any route that must be
    restricted to specific roles, e.g. Depends(require_roles(UserRole.ADMIN))."""

    async def _guard(ctx: AuthContext = Depends(get_current_user)) -> AuthContext:
        if ctx.role not in allowed_roles:
            raise ForbiddenError(f"Role '{ctx.role.value}' is not permitted for this action")
        return ctx

    return _guard
