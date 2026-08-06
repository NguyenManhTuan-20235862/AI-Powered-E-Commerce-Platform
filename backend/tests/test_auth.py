"""Test cho POST /auth/register và POST /auth/login (task 1.3.2)."""

from fastapi.testclient import TestClient

VALID_PAYLOAD = {
    "email": "customer@example.com",
    "password": "password123",
    "full_name": "Nguyen Van A",
}


def test_register_success(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json=VALID_PAYLOAD)
    assert response.status_code == 201

    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == VALID_PAYLOAD["email"]
    assert body["data"]["role"] == "customer"
    assert "password" not in body["data"]
    assert "password_hash" not in body["data"]


def test_register_duplicate_email_returns_400(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=VALID_PAYLOAD)
    response = client.post("/api/v1/auth/register", json=VALID_PAYLOAD)
    assert response.status_code == 400


def test_register_cannot_set_role(client: TestClient) -> None:
    payload = {**VALID_PAYLOAD, "role": "admin"}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["data"]["role"] == "customer"


def test_login_success(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=VALID_PAYLOAD)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": VALID_PAYLOAD["email"], "password": VALID_PAYLOAD["password"]},
    )
    assert response.status_code == 200

    body = response.json()
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["access_token"]
    assert body["data"]["refresh_token"]


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=VALID_PAYLOAD)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": VALID_PAYLOAD["email"], "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_login_unknown_email_returns_401(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "no-such-user@example.com", "password": "password123"},
    )
    assert response.status_code == 401
