"""
Seed driver user into DB and test Driver Chatbot Intents against live API server (http://127.0.0.1:8000)
"""
import asyncio
import json
import urllib.request
import urllib.error
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"
DRIVER_EMAIL = "driver_demo@gorush.com"
DRIVER_PASS = "password123"

DRIVER_TEST_QUERIES = [
    # Working baseline
    "Aaj meri total earning kitni hai?",
    # Problematic Case 1: Passenger damaged vehicle
    "The passenger damaged my vehicle.",
    # Problematic Case 2: Payment arrival inquiry (EN)
    "When will my payment arrive?",
    # Problematic Case 3: Payment not received (Hinglish)
    "Payment abhi tak nahi aayi hai.",
    # Problematic Case 4: Passenger not found
    "Mera passenger mujhe nahi mil raha.",
    # Problematic Case 5: Driver verification pending
    "Mera driver verification pending hai.",
    # Problematic Case 6: Cancellation fee eligibility
    "Passenger ne ride cancel kar di, mujhe cancellation fee milegi?",
    # Problematic Case 7: Driver incentive delay
    "Mera incentive abhi tak nahi mila.",
    # Problematic Case 8: Human agent handoff
    "Mujhe driver support agent se baat karni hai.",
    # Problematic Case 9: Passenger threat
    "Passenger mujhe threaten kar raha hai.",
    # Problematic Case 10: Feeling unsafe with passenger
    "I don't feel safe with this passenger.",
]


async def seed_driver():
    try:
        from sqlalchemy import select
        from app.auth.security import hash_password
        from app.database.session import AsyncSessionLocal
        from app.users.models import User
        from app.common.enums.chat import UserRole

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.external_ref == DRIVER_EMAIL))
            user = result.scalar_one_or_none()
            if user is None:
                user = User(
                    external_ref=DRIVER_EMAIL,
                    role=UserRole.DRIVER.value if hasattr(UserRole.DRIVER, 'value') else "driver",
                    hashed_password=hash_password(DRIVER_PASS),
                    preferred_language="en",
                    is_active=True,
                )
                session.add(user)
                await session.commit()
                print(f"[+] Created driver user: {DRIVER_EMAIL}", flush=True)
            else:
                print(f"[+] Driver user already exists: {DRIVER_EMAIL}", flush=True)
    except Exception as e:
        print(f"[!] Warning seeding user: {e}", flush=True)


def http_post(url: str, data: dict, headers: dict = None) -> dict:
    headers = headers or {}
    headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"HTTP Error {e.code}: {body}", flush=True)
        raise e


def test_api():
    print("\n--- 1. Logging in as Driver ---", flush=True)
    login_res = http_post(f"{BASE_URL}/v1/auth/login", {
        "external_ref": DRIVER_EMAIL,
        "password": DRIVER_PASS
    })
    token = login_res.get("access_token")
    role = login_res.get("role")
    print(f"Auth Success! Role: {role}", flush=True)
    headers = {"Authorization": f"Bearer {token}"}

    print("\n--- 2. Creating Chat Session ---", flush=True)
    session_res = http_post(f"{BASE_URL}/v1/chat/sessions", {"language": "en"}, headers=headers)
    session_id = session_res["data"]["session_id"]
    print(f"Session Created! ID: {session_id}", flush=True)

    print("\n--- 3. Testing Driver Chatbot Messages ---", flush=True)
    print("=" * 70, flush=True)

    for message in DRIVER_TEST_QUERIES:
        print(f"Sending message: \"{message}\"...", flush=True)
        res = http_post(f"{BASE_URL}/v1/chat/messages", {
            "session_id": session_id,
            "message": message
        }, headers=headers)

        data = res["data"]
        print(f"Driver Input:    \"{message}\"", flush=True)
        print(f"Detected Intent: {data.get('intent')}", flush=True)
        print(f"Language:        {data.get('language')}", flush=True)
        print(f"Bot Response:    {data.get('message')}", flush=True)
        print(f"Actions:         {data.get('actions')}", flush=True)
        print(f"Handoff Status:  {data.get('handoff')}", flush=True)
        print("-" * 70, flush=True)


def main():
    asyncio.run(seed_driver())
    test_api()


if __name__ == "__main__":
    main()
