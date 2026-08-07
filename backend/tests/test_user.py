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
