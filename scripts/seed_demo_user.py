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
        from sqlalchemy import select
        for ref, pwd in [("demo-customer", "demo@123"), ("demo-customer-1", "demo-password")]:
            res = await db.execute(select(User).where(User.external_ref == ref))
            existing = res.scalar_one_or_none()
            if not existing:
                u = User(
                    external_ref=ref,
                    role=UserRole.CUSTOMER,
                    preferred_language="en",
                    hashed_password=hash_password(pwd),
                )
                db.add(u)
                await db.commit()
                print(f"Created demo user external_ref={ref} password={pwd}")
            else:
                print(f"Demo user external_ref={ref} already exists.")


if __name__ == "__main__":
    asyncio.run(main())
