import time
from fastapi.testclient import TestClient
from src.api.s import app
from src.storage.user_db import create_user, get_user


def unique_email():
    return f"test_user_{int(time.time() * 1000)}@example.com"


def test_purchase_verify_idempotency():
    client = TestClient(app)
    email = unique_email()
    # create user (ignore duplicate error)
    try:
        create_user(email, 30, "x", "pass1234")
    except ValueError:
        pass

    # read initial chats
    before = get_user(email)
    initial_chats = before[5] if before and len(before) > 5 else 0

    payload = {
        "email": email,
        "purchase_token": "test-token-12345",
        "product_id": "mental_health_5_chats_v1"
    }

    # First call should add chats
    r1 = client.post("/purchase/verify", json=payload)
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1.get("success") is True
    assert body1.get("chats_added") == 5

    # Second call with same token should be idempotent
    r2 = client.post("/purchase/verify", json=payload)
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2.get("success") is True
    # chats_added should be 0 for already-processed token
    assert body2.get("chats_added") == 0

    # Confirm DB reflects only one addition
    after = get_user(email)
    final_chats = after[5] if after and len(after) > 5 else 0
    assert final_chats == initial_chats + 5
