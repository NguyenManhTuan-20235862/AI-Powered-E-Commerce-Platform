"""Test JWT blacklist qua Redis (task 3.3.2) - end-to-end qua HTTP thật
(POST /auth/logout, không chỉ unit test hàm rời) vì hành vi này cắt ngang
nhiều lớp (router + get_current_user dependency + Redis thật, container
compose service `redis`, không mock - cùng triết lý MySQL/Redis thật đã
dùng xuyên suốt dự án, xem tests/conftest.py).
"""

import redis as redis_lib
from fastapi.testclient import TestClient

from app.core.database import get_redis
from app.main import app

VALID_PAYLOAD = {
    "email": "logout-test@example.com",
    "password": "password123",
    "full_name": "Logout Test User",
}


def _register(client: TestClient) -> None:
    client.post("/api/v1/auth/register", json=VALID_PAYLOAD)


def _login(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": VALID_PAYLOAD["email"], "password": VALID_PAYLOAD["password"]},
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_logout_blacklists_token_then_new_login_still_works(client: TestClient) -> None:
    _register(client)
    tokens = _login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Token còn hiệu lực - gọi API cần auth thành công (dùng /auth/me, đã
    # implement thật, không phải placeholder 501).
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    # Logout - blacklist chính token đang dùng.
    logout_response = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_response.status_code == 200
    assert logout_response.json()["success"] is True

    # CÙNG token cũ - phải bị từ chối ngay (401), dù chưa hết hạn tự nhiên.
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401

    # Login LẠI - token MỚI (jti khác) vẫn hoạt động bình thường, không bị
    # ảnh hưởng bởi việc blacklist token cũ.
    new_tokens = _login(client)
    assert new_tokens["access_token"] != tokens["access_token"]
    new_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=new_headers).status_code == 200


def test_logout_does_not_affect_other_sessions_same_user(client: TestClient) -> None:
    """2 token khác nhau (VD 2 thiết bị) cho CÙNG 1 user - logout ở token A
    KHÔNG ảnh hưởng token B (mỗi token có "jti" riêng, xem create_access_token) -
    đúng như lý do chọn jti thay vì blacklist theo user_id."""
    _register(client)
    tokens_a = _login(client)
    tokens_b = _login(client)
    assert tokens_a["access_token"] != tokens_b["access_token"]

    client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {tokens_a['access_token']}"})

    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens_a['access_token']}"}).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens_b['access_token']}"}).status_code == 200


def test_auth_still_works_when_redis_down_fail_open(client: TestClient) -> None:
    """Redis KHÔNG kết nối được lúc check blacklist - PHẢI fail-open (quyết
    định đã xác nhận với người dùng, task 3.3.2): token hợp lệ (chưa từng bị
    blacklist) vẫn được chấp nhận bình thường, KHÔNG bị 401 chỉ vì Redis down -
    đổi lấy việc Redis không trở thành single point of failure cho toàn bộ
    endpoint cần đăng nhập.
    """
    _register(client)
    tokens = _login(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    broken_redis = redis_lib.from_url(
        "redis://:wrong-password@nonexistent-host-for-test:6379/0",
        decode_responses=True,
        socket_connect_timeout=1,
        socket_timeout=1,
    )
    app.dependency_overrides[get_redis] = lambda: broken_redis
    try:
        response = client.get("/api/v1/auth/me", headers=headers)
    finally:
        del app.dependency_overrides[get_redis]

    assert response.status_code == 200
