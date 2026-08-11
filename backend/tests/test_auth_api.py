def test_register_and_me(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "authtest@example.com", "password": "Password123", "full_name": "Auth Test"},
    )
    assert resp.status_code == 201
    assert resp.json()["email"] == "authtest@example.com"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "authtest@example.com"


def test_duplicate_registration_rejected(client):
    payload = {"email": "dupe@example.com", "password": "Password123"}
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 201
    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 409


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={"email": "loginfail@example.com", "password": "Password123"})
    resp = client.post("/api/auth/login", json={"email": "loginfail@example.com", "password": "WrongPassword"})
    assert resp.status_code == 401


def test_unauthenticated_chat_rejected(client):
    resp = client.post("/api/chat", json={"message": "hello"})
    assert resp.status_code == 401


def test_logout_clears_session(registered_client):
    resp = registered_client.post("/api/auth/logout")
    assert resp.status_code == 200
    me = registered_client.get("/api/auth/me")
    assert me.status_code == 401
