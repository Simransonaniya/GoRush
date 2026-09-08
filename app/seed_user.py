import asyncio

from app.auth.security import hash_password
from app.database.session import AsyncSessionLocal
from app.users.models import User
from app.common.enums.chat import UserRole


async def seed():
    async with AsyncSessionLocal() as session:
        user = User(
            external_ref="simran77@gmail.com",
            role=UserRole.CUSTOMER,
            hashed_password=hash_password("password@123"),
            preferred_language="en",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        print(f"Created user: {user.external_ref} (id={user.id}, role={user.role})")


if __name__ == "__main__":
    asyncio.run(seed())
