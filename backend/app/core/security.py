"""Xác thực JWT + phân quyền theo role (task 1.3.3).

`get_current_user` decode access token thật, load User từ MySQL. `require_role`
là dependency factory chặn endpoint theo role (403 nếu sai role, phân biệt với
401 nếu chưa xác thực).
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User, UserRole

# tokenUrl chỉ dùng để Swagger UI biết endpoint lấy token khi bấm nút "Authorize".
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


def _unauthorized() -> HTTPException:
    """1 message lỗi DUY NHẤT cho mọi lý do 401 (thiếu token, sai định dạng, hết
    hạn, sai chữ ký, user không tồn tại, tài khoản bị khóa) - tránh lộ chi tiết
    lý do cụ thể ra ngoài (VD: phân biệt "token sai" với "user không tồn tại"
    có thể lộ thông tin cho kẻ tấn công dò hệ thống)."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Không thể xác thực - vui lòng đăng nhập lại",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Decode access token JWT thật, trả về User (SQLAlchemy model) tương ứng.

    Trả về ORM model (không phải Pydantic schema) vì:
    - Route/service layer sau này (Order, Cart...) sẽ cần current_user.id để
      filter dữ liệu theo chủ sở hữu - dùng thẳng model tránh phải query lại.
    - Nhất quán với app/services/auth_service.py (cũng trả về User model).
    - Session từ get_db() còn mở xuyên suốt request nên không có rủi ro
      DetachedInstanceError khi đọc field trong route handler.
    """
    if not token:
        raise _unauthorized()

    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise _unauthorized()

    if payload.get("type") != "access":
        raise _unauthorized()

    user_id = payload.get("sub")
    if user_id is None:
        raise _unauthorized()

    try:
        user = db.get(User, int(user_id))
    except (TypeError, ValueError):
        raise _unauthorized()

    if user is None or not user.is_active:
        raise _unauthorized()

    return user


def require_role(*allowed_roles: UserRole):
    """Dependency factory: chặn endpoint theo role, dùng SAU get_current_user.

    Trả 403 (không phải 401) vì user đã xác thực hợp lệ nhưng role không đủ
    quyền - phân biệt rõ "chưa đăng nhập" với "đăng nhập rồi nhưng không có quyền".

    Dùng như dependency của param (khuyến nghị - trả thẳng User cho route dùng
    tiếp ở business logic sau này):
        current_user: Annotated[User, Depends(require_role(UserRole.admin))]
    hoặc dùng dạng gate-only ở decorator nếu route không cần current_user:
        @router.get(..., dependencies=[Depends(require_role(UserRole.admin))])
    """

    def dependency(current_user: Annotated[User, Depends(get_current_user)]) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Không đủ quyền truy cập",
            )
        return current_user

    return dependency


# ---- JWT + password hashing (task 1.3.2 - /auth/register, /auth/login) ----

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash mật khẩu bằng bcrypt (passlib) - dùng khi đăng ký / đổi mật khẩu."""
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """So khớp mật khẩu plain text với hash đã lưu trong DB - dùng khi đăng nhập."""
    return _pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: int, role: str) -> str:
    """Tạo access token JWT (thời hạn ngắn, settings.ACCESS_TOKEN_EXPIRE_MINUTES)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Tạo refresh token JWT (thời hạn dài, settings.REFRESH_TOKEN_EXPIRE_DAYS).

    TODO (task sau): endpoint /auth/refresh decode + verify token này
    (claim "type": "refresh") để cấp access token mới; hiện /auth/refresh vẫn
    là placeholder 501.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
