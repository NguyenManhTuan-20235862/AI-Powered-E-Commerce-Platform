"""Test cho get_current_user (JWT thật) và require_role (task 1.3.3).

Lúc viết file này (task 1.3.3), chưa endpoint nào trả 200 thật (toàn bộ
router vẫn placeholder 501) nên "đúng role" được xác nhận bằng việc request
VƯỢT QUA được lớp auth/role và chạm tới 501 thay vì bị chặn ở 401/403 - hầu
hết router đã implement thật từ lâu (chỉ còn vài endpoint AI Agent task 6.x
là 501), các test dưới đây CHỦ ĐÍCH vẫn kiểm tra ĐÚNG lớp auth/role (không
quan tâm response THÀNH CÔNG cụ thể ra sao), chỉ riêng
`test_valid_token_passes_auth_reaches_real_logic` từng dựa vào 1 endpoint đã
là placeholder, nay endpoint đó đã real nên đổi kỳ vọng sang mã lỗi nghiệp vụ
thật (404) thay vì 501.
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


def _create_user(db: Session, *, role: UserRole, is_active: bool = True) -> User:
    user = User(
        email=f"{role.value}-{datetime.now().timestamp()}@example.com",
        password_hash=hash_password("password123"),
        full_name="Test User",
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _expired_token(user_id: int) -> str:
    """Tự ký 1 token đã hết hạn (exp ở quá khứ) - không dùng create_access_token
    vì hàm đó luôn set exp trong tương lai."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": UserRole.customer.value,
        "type": "access",
        "iat": now - timedelta(minutes=10),
        "exp": now - timedelta(minutes=5),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def test_no_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_malformed_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert response.status_code == 401


def test_expired_token_returns_401(client: TestClient, db: Session) -> None:
    user = _create_user(db, role=UserRole.customer)
    token = _expired_token(user.id)
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_locked_account_returns_401(client: TestClient, db: Session) -> None:
    user = _create_user(db, role=UserRole.customer, is_active=False)
    token = create_access_token(user_id=user.id, role=user.role.value)
    response = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_valid_token_passes_auth_reaches_real_logic(client: TestClient, db: Session) -> None:
    """Token hợp lệ, endpoint không giới hạn role cụ thể (Customer, Admin đều được).

    Dùng /payments/{order_id}/status - vẫn dùng LẠI đúng endpoint này (không
    yêu cầu role cụ thể, `Depends(get_current_user)` thuần, xem
    app/routers/payment.py) nhưng KHÔNG còn là placeholder `501` (implement
    thật ở task "Quyết định và hoàn thiện thanh toán", xem test_payment.py) -
    order_id không tồn tại (999999) giờ trả `404` THẬT (đã vượt qua auth,
    chạm tới logic thật kiểm tra đơn hàng có tồn tại hay không) thay vì `501`.
    """
    user = _create_user(db, role=UserRole.customer)
    token = create_access_token(user_id=user.id, role=user.role.value)
    response = client.get("/api/v1/payments/999999/status", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 404


def test_customer_token_on_admin_only_endpoint_returns_403(client: TestClient, db: Session) -> None:
    user = _create_user(db, role=UserRole.customer)
    token = create_access_token(user_id=user.id, role=user.role.value)
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_admin_token_on_admin_only_endpoint_passes_role_check(client: TestClient, db: Session) -> None:
    """`GET /users` (task Quản lý người dùng Admin, implement thật) không còn
    là placeholder 501 - trả 200 thật (role check pass, danh sách user thật)."""
    user = _create_user(db, role=UserRole.admin)
    token = create_access_token(user_id=user.id, role=user.role.value)
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_admin_token_on_customer_only_endpoint_returns_403(client: TestClient, db: Session) -> None:
    """Cart chỉ dành cho Customer - Admin phải bị chặn 403."""
    user = _create_user(db, role=UserRole.admin)
    token = create_access_token(user_id=user.id, role=user.role.value)
    response = client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_customer_token_on_customer_only_endpoint_passes_role_check(client: TestClient, db: Session) -> None:
    """GET /cart (task 3.4.2, implement thật) không còn là placeholder 501 -
    trả 200 thật (giỏ hàng rỗng, user vừa tạo chưa thêm gì)."""
    user = _create_user(db, role=UserRole.customer)
    token = create_access_token(user_id=user.id, role=user.role.value)
    response = client.get("/api/v1/cart", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
