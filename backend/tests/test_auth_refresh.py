"""Test cho `POST /auth/refresh` thật (auth/session hardening task) - 4 case
bắt buộc theo yêu cầu: token hết hạn, refresh token sai loại (dùng nhầm access
token), refresh token bị revoke (blacklist qua logout), user bị khóa.

Cùng convention `test_security.py` (tự ký token bằng `jose.jwt` cho case
hết hạn/sai loại - `create_access_token`/`create_refresh_token` luôn set
`exp` tương lai và đúng `type`, không tạo được token "sai" bằng 2 hàm đó).
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.models.user import User, UserRole


def _create_user(db: Session, *, role: UserRole = UserRole.customer, is_active: bool = True) -> User:
    user = User(
        email=f"{role.value}-refresh-{datetime.now().timestamp()}@example.com",
        password_hash=hash_password("password123"),
        full_name="Refresh Test User",
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _expired_refresh_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now - timedelta(days=10),
        "exp": now - timedelta(days=1),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def test_refresh_success_issues_new_access_token_same_refresh_token(client: TestClient, db: Session) -> None:
    user = _create_user(db)
    refresh_token = create_refresh_token(user_id=user.id)

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200, response.text

    body = response.json()["data"]
    assert body["access_token"]
    # Không rotate - refresh token trả về PHẢI giống hệt token đã gửi lên.
    assert body["refresh_token"] == refresh_token

    # Access token mới dùng được ngay.
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["data"]["id"] == user.id


def test_refresh_with_access_token_wrong_type_returns_401(client: TestClient, db: Session) -> None:
    """Dùng nhầm ACCESS token (type="access") ở field refresh_token - phải bị
    từ chối, không được coi là hợp lệ chỉ vì chữ ký đúng."""
    user = _create_user(db)
    access_token = create_access_token(user_id=user.id, role=user.role.value)

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": access_token})
    assert response.status_code == 401


def test_refresh_with_expired_refresh_token_returns_401(client: TestClient, db: Session) -> None:
    user = _create_user(db)
    token = _expired_refresh_token(user.id)

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert response.status_code == 401


def test_refresh_with_malformed_token_returns_401(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-jwt"})
    assert response.status_code == 401


def test_refresh_with_revoked_refresh_token_returns_401(client: TestClient, db: Session) -> None:
    """Logout kèm refresh_token trong body -> blacklist -> refresh sau đó bằng
    ĐÚNG token này phải bị từ chối (dù chưa hết hạn tự nhiên)."""
    user = _create_user(db)
    access_token = create_access_token(user_id=user.id, role=user.role.value)
    refresh_token = create_refresh_token(user_id=user.id)

    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert logout_response.status_code == 200

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


def test_refresh_with_locked_user_returns_401(client: TestClient, db: Session) -> None:
    user = _create_user(db)
    refresh_token = create_refresh_token(user_id=user.id)

    user.is_active = False
    db.commit()

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


def test_logout_without_refresh_token_in_body_still_succeeds(client: TestClient, db: Session) -> None:
    """Body rỗng/thiếu refresh_token vẫn logout thành công (chỉ access token
    bị blacklist) - refresh_token trong body là optional, KHÔNG bắt buộc."""
    user = _create_user(db)
    access_token = create_access_token(user_id=user.id, role=user.role.value)

    response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200

    response_with_empty_body = client.post(
        "/api/v1/auth/logout",
        json={},
        headers={"Authorization": f"Bearer {create_access_token(user_id=user.id, role=user.role.value)}"},
    )
    assert response_with_empty_body.status_code == 200
