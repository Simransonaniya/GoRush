"""
Usage: python -m scripts.seed_demo_user
Creates one demo customer for local login/testing.
"""
import asyncio

from app.auth.security import hash_password
from app.common.enums.chat import UserRole
from app.database.session import AsyncSessionLocal
from app.users.models import User


async def main() -> None:
    async with AsyncSessionLocal() as db:
        user = User(
            external_ref="demo-customer-1",
            role=UserRole.CUSTOMER,
            preferred_language="en",
            hashed_password=hash_password("demo-password"),
        )
        db.add(user)
        await db.commit()
        print(f"Created demo user id={user.id} external_ref=demo-customer-1 password=demo-password")


if __name__ == "__main__":
    asyncio.run(main())
