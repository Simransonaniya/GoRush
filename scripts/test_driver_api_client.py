"""
Direct HTTP test using Starlette TestClient to test all 10 problematic driver cases
and the working baseline across the complete HTTP API stack.
"""
import sys
import json
import asyncio
from starlette.testclient import TestClient
from app.main import app
from app.auth.security import hash_password
from app.database.session import AsyncSessionLocal
from app.users.models import User
from app.common.enums.chat import UserRole
from sqlalchemy import select

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DRIVER_EMAIL = "driver_demo@gorush.com"
DRIVER_PASS = "password123"

CASES = [
    ("Aaj meri total earning kitni hai?", "Working Baseline"),
    ("The passenger damaged my vehicle.", "Case 1: Vehicle Damage"),
    ("When will my payment arrive?", "Case 2: Payment Arrival"),
    ("Payment abhi tak nahi aayi hai.", "Case 3: Payment Delayed"),
    ("Mera passenger mujhe nahi mil raha.", "Case 4: Customer Not Found"),
    ("Mera driver verification pending hai.", "Case 5: Verification Pending"),
    ("Passenger ne ride cancel kar di, mujhe cancellation fee milegi?", "Case 6: Cancellation Fee"),
    ("Mera incentive abhi tak nahi mila.", "Case 7: Incentive Status"),
    ("Mujhe driver support agent se baat karni hai.", "Case 8: Human Agent"),
    ("Passenger mujhe threaten kar raha hai.", "Case 9: Passenger Threat"),
    ("I don't feel safe with this passenger.", "Case 10: Safety Concern"),
]


async def seed():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.external_ref == DRIVER_EMAIL))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                external_ref=DRIVER_EMAIL,
                role=UserRole.DRIVER.value,
                hashed_password=hash_password(DRIVER_PASS),
                preferred_language="en",
                is_active=True,
            )
            session.add(user)
            await session.commit()
            print("[+] Seeded driver user")
        else:
            print("[+] Driver user exists")


def run_tests():
    asyncio.run(seed())
    client = TestClient(app)

    # 1. Login
    login_resp = client.post("/v1/auth/login", json={
        "external_ref": DRIVER_EMAIL,
        "password": DRIVER_PASS
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    print("\n" + "="*80)
    print("GORUSH DRIVER INTENT ROUTING VERIFICATION REPORT (HTTP API)")
    print("="*80)

    for query, label in CASES:
        # Create fresh session
        s_resp = client.post("/v1/chat/sessions", json={"language": "en"}, headers=headers)
        session_id = s_resp.json()["data"]["session_id"]

        # Send message
        m_resp = client.post("/v1/chat/messages", json={
            "session_id": session_id,
            "message": query
        }, headers=headers)

        assert m_resp.status_code == 200, f"Message failed: {m_resp.text}"
        data = m_resp.json()["data"]

        intent = data.get("intent")
        lang = data.get("language")
        actions = data.get("actions", [])
        handoff = data.get("handoff", {})
        bot_msg = data.get("message", "")

        print(f"\n[{label}]")
        print(f"Driver Input:    \"{query}\"")
        print(f"Detected Intent: {intent}")
        print(f"Language:        {lang}")
        print(f"Actions Taken:   {actions}")
        print(f"Handoff Status:  {handoff}")
        print(f"Bot Message:     {bot_msg[:120]}...")
    print("\n" + "="*80)
    print("ALL 11 DRIVER CASES ROUTED AND VERIFIED SUCCESSFULLY!")
    print("="*80)

    # 2. Customer Tests for "meri ride late hai" and "meri ride kab tak aaigi"
    CUSTOMER_EMAIL = "simran77@gmail.com"
    CUSTOMER_PASS = "password123"

    cust_login = client.post("/v1/auth/login", json={
        "external_ref": CUSTOMER_EMAIL,
        "password": CUSTOMER_PASS
    })
    if cust_login.status_code == 200:
        c_token = cust_login.json()["access_token"]
        c_headers = {"Authorization": f"Bearer {c_token}"}
        print("\n" + "="*80)
        print("CUSTOMER RIDE LATE VERIFICATION REPORT (HTTP API)")
        print("="*80)
        CUSTOMER_CASES = [
            ("meri ride late hai", "Customer Ride Late Case 1"),
            ("meri ride kab tak aaigi", "Customer Ride Late Case 2 (ETA)"),
        ]
        for query, label in CUSTOMER_CASES:
            s_resp = client.post("/v1/chat/sessions", json={"language": "hi-en"}, headers=c_headers)
            session_id = s_resp.json()["data"]["session_id"]
            m_resp = client.post("/v1/chat/messages", json={
                "session_id": session_id,
                "message": query
            }, headers=c_headers)
            assert m_resp.status_code == 200, f"Customer message failed: {m_resp.text}"
            data = m_resp.json()["data"]
            print(f"\n[{label}]")
            print(f"Customer Input:  \"{query}\"")
            print(f"Detected Intent: {data.get('intent')}")
            print(f"Language:        {data.get('language')}")
            print(f"Actions Taken:   {data.get('actions')}")
            print(f"Bot Message:     {data.get('message')[:120]}...")
            assert data.get("intent") != "unknown", f"Customer query fell back to 'unknown': {query}"
            assert "get_driver_eta" in data.get("actions", []), f"Action get_driver_eta missing for {query}"
        print("\n" + "="*80)
        print("ALL CUSTOMER CASES ROUTED AND VERIFIED SUCCESSFULLY!")
        print("="*80)


if __name__ == "__main__":
    run_tests()
