"""
E2E HTTP integration test for POST /v1/chat/messages endpoint.

Verifies end-to-end HTTP pipeline:
  POST /v1/chat/messages
  -> Auth Dependency (JWT validation & AuthContext)
  -> Rate Limiter
  -> ChatOrchestrator
  -> IntentDetector ("ride_status")
  -> ToolRouter & GetActiveRideTool execution
  -> Real Tool Result ("ride_123")
  -> Response Generation
  -> API Response with actions = ["get_active_ride"]
"""
import uuid
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.auth.security import create_access_token, hash_password
from app.common.enums.chat import UserRole
from app.database.session import AsyncSessionLocal, Base, engine
from app.users.models import User


@pytest.mark.asyncio
async def test_e2e_http_chat_messages_get_active_ride():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    driver_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async with AsyncSessionLocal() as db:
        user = User(
            id=driver_id,
            external_ref=f"driver_{driver_id}@gorush.com",
            role=UserRole.DRIVER.value,
            hashed_password=hash_password("password123"),
            preferred_language="en",
            is_active=True,
        )
        db.add(user)
        await db.commit()

        # Create session directly in DB for test
        from app.chat.models import ChatSession
        chat_sess = ChatSession(id=session_id, user_id=driver_id, language="en", status="active")
        db.add(chat_sess)
        await db.commit()

    token = create_access_token(subject=str(driver_id), role=UserRole.DRIVER.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/v1/chat/messages",
            json={"session_id": str(session_id), "message": "Where is my active ride?"},
            headers=headers,
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        payload = response.json()

        assert payload.get("success") is True
        data = payload.get("data", {})
        assert data.get("intent") == "ride_status"
        assert data.get("actions") == ["get_active_ride"]
        assert "ride_123" in data.get("message", "") or "active ride" in data.get("message", "").lower()
        assert "I am GoRush Assistant. I can assist you" not in data.get("message", "")


@pytest.mark.asyncio
async def test_e2e_http_chat_messages_hindi_active_ride():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    driver_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async with AsyncSessionLocal() as db:
        user = User(
            id=driver_id,
            external_ref=f"driver_{driver_id}@gorush.com",
            role=UserRole.DRIVER.value,
            hashed_password=hash_password("password123"),
            preferred_language="hi",
            is_active=True,
        )
        db.add(user)
        await db.commit()

        from app.chat.models import ChatSession
        chat_sess = ChatSession(id=session_id, user_id=driver_id, language="hi", status="active")
        db.add(chat_sess)
        await db.commit()

    token = create_access_token(subject=str(driver_id), role=UserRole.DRIVER.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/v1/chat/messages",
            json={"session_id": str(session_id), "message": "मेरी एक्टिव राइड कहाँ है?"},
            headers=headers,
        )

        assert response.status_code == 200, response.text
        payload = response.json()
        data = payload.get("data", {})
        assert data.get("language") == "hi"
        assert data.get("intent") == "ride_status"
        assert data.get("actions") == ["get_active_ride"]
        assert "ride_123" in data.get("message", "") or "एक्टिव" in data.get("message", "")


@pytest.mark.asyncio
async def test_e2e_http_p0_emergency_accident():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    driver_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async with AsyncSessionLocal() as db:
        user = User(
            id=driver_id, external_ref=f"driver_{driver_id}@gorush.com",
            role=UserRole.DRIVER.value, hashed_password=hash_password("password123"),
            preferred_language="en", is_active=True,
        )
        db.add(user)
        await db.commit()

        from app.chat.models import ChatSession
        chat_sess = ChatSession(id=session_id, user_id=driver_id, language="en", status="active")
        db.add(chat_sess)
        await db.commit()

    token = create_access_token(subject=str(driver_id), role=UserRole.DRIVER.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/v1/chat/messages",
            json={"session_id": str(session_id), "message": "I have been in an accident and need help immediately."},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        data = payload.get("data", {})
        assert data.get("intent") == "safety"
        assert "create_safety_incident" in data.get("actions", [])
        handoff = data.get("handoff", {})
        assert handoff.get("triggered") is True
        assert handoff.get("priority") == "P0"


@pytest.mark.asyncio
async def test_e2e_http_p1_account_hacked():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    driver_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async with AsyncSessionLocal() as db:
        user = User(
            id=driver_id, external_ref=f"driver_{driver_id}@gorush.com",
            role=UserRole.DRIVER.value, hashed_password=hash_password("password123"),
            preferred_language="en", is_active=True,
        )
        db.add(user)
        await db.commit()

        from app.chat.models import ChatSession
        chat_sess = ChatSession(id=session_id, user_id=driver_id, language="en", status="active")
        db.add(chat_sess)
        await db.commit()

    token = create_access_token(subject=str(driver_id), role=UserRole.DRIVER.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/v1/chat/messages",
            json={"session_id": str(session_id), "message": "Someone hacked my driver account."},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        data = payload.get("data", {})
        handoff = data.get("handoff", {})
        assert handoff.get("triggered") is True
        assert handoff.get("priority") == "P1"


@pytest.mark.asyncio
async def test_e2e_http_p3_faq_cancellation_policy():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    driver_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async with AsyncSessionLocal() as db:
        user = User(
            id=driver_id, external_ref=f"driver_{driver_id}@gorush.com",
            role=UserRole.DRIVER.value, hashed_password=hash_password("password123"),
            preferred_language="en", is_active=True,
        )
        db.add(user)
        await db.commit()

        from app.chat.models import ChatSession
        chat_sess = ChatSession(id=session_id, user_id=driver_id, language="en", status="active")
        db.add(chat_sess)
        await db.commit()

    token = create_access_token(subject=str(driver_id), role=UserRole.DRIVER.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/v1/chat/messages",
            json={"session_id": str(session_id), "message": "What is the cancellation policy?"},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        data = payload.get("data", {})
        assert data.get("actions") == []
        handoff = data.get("handoff", {})
        assert handoff.get("triggered") is False


@pytest.mark.asyncio
async def test_e2e_http_p0_hindi_accident_exact():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    driver_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async with AsyncSessionLocal() as db:
        user = User(
            id=driver_id, external_ref=f"driver_{driver_id}@gorush.com",
            role=UserRole.DRIVER.value, hashed_password=hash_password("password123"),
            preferred_language="hi", is_active=True,
        )
        db.add(user)
        await db.commit()

        from app.chat.models import ChatSession
        chat_sess = ChatSession(id=session_id, user_id=driver_id, language="hi", status="active")
        db.add(chat_sess)
        await db.commit()

    token = create_access_token(subject=str(driver_id), role=UserRole.DRIVER.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/v1/chat/messages",
            json={"session_id": str(session_id), "message": "मेरा एक्सीडेंट हो गया है और मुझे तुरंत मदद चाहिए।"},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        data = payload.get("data", {})
        assert data.get("language") == "hi"
        assert data.get("intent") == "safety"
        assert "create_safety_incident" in data.get("actions", [])
        handoff = data.get("handoff", {})
        assert handoff.get("triggered") is True
        assert handoff.get("priority") == "P0"


@pytest.mark.asyncio
async def test_e2e_http_p0_hinglish_accident():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    driver_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async with AsyncSessionLocal() as db:
        user = User(
            id=driver_id, external_ref=f"driver_{driver_id}@gorush.com",
            role=UserRole.DRIVER.value, hashed_password=hash_password("password123"),
            preferred_language="hi-en", is_active=True,
        )
        db.add(user)
        await db.commit()

        from app.chat.models import ChatSession
        chat_sess = ChatSession(id=session_id, user_id=driver_id, language="hi-en", status="active")
        db.add(chat_sess)
        await db.commit()

    token = create_access_token(subject=str(driver_id), role=UserRole.DRIVER.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post(
            "/v1/chat/messages",
            json={"session_id": str(session_id), "message": "Mera accident ho gaya hai, mujhe abhi help chahiye."},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        data = payload.get("data", {})
        assert data.get("language") == "hi-en"
        assert data.get("intent") == "safety"
        assert "create_safety_incident" in data.get("actions", [])
        handoff = data.get("handoff", {})
        assert handoff.get("triggered") is True
        assert handoff.get("priority") == "P0"


@pytest.mark.asyncio
async def test_e2e_http_guided_refund_flow():
    """Verify multi-turn refund flow via POST /v1/chat/messages endpoint:
    Turn 1: 'Meri last ride ka refund chahiye.' -> Verifies ride/payment/refund -> Guides user and asks for confirmation
    Turn 2: 'Haan kar do' -> Executes request_refund -> Confirms submission with real backend refund ID.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    customer_id = uuid.uuid4()
    session_id = uuid.uuid4()

    async with AsyncSessionLocal() as db:
        user = User(
            id=customer_id,
            external_ref=f"cust_{customer_id}@gorush.com",
            role=UserRole.CUSTOMER.value,
            hashed_password=hash_password("password123"),
            preferred_language="hi-en",
            is_active=True,
        )
        db.add(user)
        await db.commit()

        from app.chat.models import ChatSession
        chat_sess = ChatSession(id=session_id, user_id=customer_id, language="hi-en", status="active")
        db.add(chat_sess)
        await db.commit()

    token = create_access_token(subject=str(customer_id), role=UserRole.CUSTOMER.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        # TURN 1
        resp1 = await client.post(
            "/v1/chat/messages",
            json={"session_id": str(session_id), "message": "Meri last ride ka refund chahiye."},
            headers=headers,
        )
        assert resp1.status_code == 200, resp1.text
        data1 = resp1.json().get("data", {})
        assert data1.get("intent") == "refund"
        assert "get_active_ride" in data1.get("actions", [])
        assert "get_payment_status" in data1.get("actions", [])
        assert "get_refund_status" in data1.get("actions", [])
        assert "eligible" in data1.get("message", "").lower() or "submit" in data1.get("message", "").lower()

        # TURN 2
        resp2 = await client.post(
            "/v1/chat/messages",
            json={"session_id": str(session_id), "message": "Haan kar do"},
            headers=headers,
        )
        assert resp2.status_code == 200, resp2.text
        data2 = resp2.json().get("data", {})
        assert data2.get("intent") == "refund"
        assert "request_refund" in data2.get("actions", [])
        assert "successfully submit" in data2.get("message", "") or "ref_ride_123" in data2.get("message", "")



