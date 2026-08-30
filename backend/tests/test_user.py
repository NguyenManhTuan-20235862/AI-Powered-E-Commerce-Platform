"""Test cho GET /users/me thật (task 1.4.1 - ví dụ minh họa dùng schema chung)
và envelope lỗi chuẩn qua exception handler trong app/main.py.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


def test_get_my_profile_returns_real_user(client: TestClient, db: Session) -> None:
    user = User(
        email="profile-test@example.com",
        password_hash=hash_password("password123"),
        full_name="Profile Test",
        role=UserRole.customer,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user_id=user.id, role=user.role.value)
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["id"] == user.id
    assert body["data"]["email"] == "profile-test@example.com"
    assert body["data"]["role"] == "customer"
    assert "password_hash" not in body["data"]
    assert "password" not in body["data"]


def test_error_response_envelope_matches_api_spec(client: TestClient) -> None:
    """401 phải theo đúng envelope {success, data, message, error_code} - không
    còn {"detail": ...} mặc định của FastAPI (xem exception handler app/main.py)."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401

    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert isinstance(body["message"], str) and body["message"]
    assert "error_code" in body
    assert "detail" not in body


# ---- GET /users, GET /users/{id}, PUT /users/{id}/status (Admin) ----


def _create_user(db: Session, *, email: str, full_name: str, role: UserRole, is_active: bool = True) -> User:
    user = User(
        email=email,
        password_hash=hash_password("password123"),
        full_name=full_name,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _admin_headers(db: Session) -> dict:
    admin = _create_user(db, email="admin-user-mgmt@example.com", full_name="Admin Test", role=UserRole.admin)
    token = create_access_token(user_id=admin.id, role=admin.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_list_users_requires_admin_role(client: TestClient, db: Session) -> None:
    customer = _create_user(db, email="cust-list@example.com", full_name="Customer", role=UserRole.customer)
    token = create_access_token(user_id=customer.id, role=customer.role.value)
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_list_users_filters_by_role_status_and_search(client: TestClient, db: Session) -> None:
    headers = _admin_headers(db)
    _create_user(db, email="nguyenvana@example.com", full_name="Nguyễn Văn A", role=UserRole.customer, is_active=True)
    _create_user(db, email="tranthib@example.com", full_name="Trần Thị B", role=UserRole.customer, is_active=False)

    response = client.get("/api/v1/users", params={"role": "customer"}, headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["total"] == 2
    assert all(item["role"] == "customer" for item in data["items"])

    response = client.get("/api/v1/users", params={"is_active": False}, headers=headers)
    assert response.json()["data"]["total"] == 1
    assert response.json()["data"]["items"][0]["email"] == "tranthib@example.com"

    response = client.get("/api/v1/users", params={"search": "Nguyễn Văn"}, headers=headers)
    body = response.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["email"] == "nguyenvana@example.com"

    response = client.get("/api/v1/users", params={"search": "tranthib@example.com"}, headers=headers)
    assert response.json()["data"]["total"] == 1


def test_get_user_detail_and_404(client: TestClient, db: Session) -> None:
    headers = _admin_headers(db)
    target = _create_user(db, email="detail-target@example.com", full_name="Detail Target", role=UserRole.customer)

    response = client.get(f"/api/v1/users/{target.id}", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["email"] == "detail-target@example.com"

    response = client.get("/api/v1/users/999999", headers=headers)
    assert response.status_code == 404


def test_lock_user_prevents_login_then_unlock_allows_login_again(client: TestClient, db: Session) -> None:
    headers = _admin_headers(db)
    target = _create_user(db, email="lock-target@example.com", full_name="Lock Target", role=UserRole.customer)
    # password thật (không qua hash_password() service) để login thật qua API -
    # _create_user() dùng "password123" cố định.
    login_payload = {"email": "lock-target@example.com", "password": "password123"}

    assert client.post("/api/v1/auth/login", json=login_payload).status_code == 200

    response = client.put(f"/api/v1/users/{target.id}/status", json={"is_active": False}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["is_active"] is False

    login_locked = client.post("/api/v1/auth/login", json=login_payload)
    assert login_locked.status_code == 403

    response = client.put(f"/api/v1/users/{target.id}/status", json={"is_active": True}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["is_active"] is True

    assert client.post("/api/v1/auth/login", json=login_payload).status_code == 200


def test_update_user_status_404_for_missing_user(client: TestClient, db: Session) -> None:
    headers = _admin_headers(db)
    response = client.put("/api/v1/users/999999/status", json={"is_active": False}, headers=headers)
    assert response.status_code == 404
