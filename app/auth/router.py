from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dto import LoginRequest, TokenResponse
from app.auth.security import create_access_token, verify_password
from app.common.exceptions.base import UnauthorizedError
from app.database.session import get_db
from app.users.models import User

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.external_ref == payload.external_ref))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise UnauthorizedError("Invalid credentials")

    token = create_access_token(subject=str(user.id), role=user.role)
    return TokenResponse(access_token=token, role=user.role)
