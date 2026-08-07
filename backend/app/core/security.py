"""Xác thực JWT + phân quyền theo role (task 1.3.3) + Redis JWT blacklist
(task 3.3.2).

`get_current_user` decode access token thật, check blacklist (Redis), load
User từ MySQL. `require_role` là dependency factory chặn endpoint theo role
(403 nếu sai role, phân biệt với 401 nếu chưa xác thực).
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

import redis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db, get_redis
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

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


def _blacklist_key(jti: str) -> str:
    """Redis key cho 1 access token đã bị blacklist (task 3.3.2, đăng xuất).

    Dùng "jti" (JWT ID, xem create_access_token) thay vì blacklist nguyên
    chuỗi token dài: (1) key Redis gọn, độ dài cố định thay vì phụ thuộc độ
    dài token thật; (2) KHÔNG lộ token thật (bearer credential dùng để xác
    thực trực tiếp) vào Redis - nếu ai đó có quyền đọc Redis (VD RedisInsight,
    dashboard vận hành), thấy được `jti` (chỉ là 1 UUID ngẫu nhiên, vô dụng
    nếu tách rời khỏi chữ ký JWT) khác hẳn với thấy được nguyên token có thể
    dùng ngay để giả mạo request.
    """
    return f"blacklist:jti:{jti}"


def is_token_blacklisted(redis_client: redis.Redis, jti: str) -> bool:
    """Check 1 jti có đang bị blacklist không (task 3.3.2).

    FAIL-OPEN nếu Redis lỗi (mất kết nối, timeout...): coi như KHÔNG bị
    blacklist, cho qua, chỉ log warning - quyết định tường minh (đã hỏi lại
    người dùng, không suy đoán): Redis hiện là 1 container ĐƠN, KHÔNG persist
    (tmpfs, xem docker-compose.yml) và KHÔNG cluster/failover - fail-closed
    (Redis lỗi -> từ chối luôn) sẽ biến Redis thành SPOF cho TOÀN BỘ endpoint
    cần đăng nhập (gần như toàn bộ API), 1 lần Redis restart/chập chờn sẽ khóa
    HẾT user ra ngoài dù MySQL/app vẫn khỏe. Đổi lại, cửa sổ rủi ro của
    fail-open rất hẹp (chỉ khi VỪA logout + ĐÚNG lúc Redis down + có ai đó cố
    dùng lại token cũ) và có TRẦN giới hạn thời gian (access token tự hết hạn
    tự nhiên sau tối đa `ACCESS_TOKEN_EXPIRE_MINUTES`) - không phải rủi ro vô
    hạn. KHÁC hẳn task 3.3.1 (cache hiệu năng, fail-open không có đánh đổi bảo
    mật) - ở đây fail-open LÀ đánh đổi bảo mật có chủ đích, không phải mặc
    định ngầm.
    """
    try:
        return redis_client.exists(_blacklist_key(jti)) > 0
    except redis.RedisError:
        logger.warning("Redis lỗi lúc check blacklist (jti=%s) - fail-open, coi như chưa bị blacklist", jti, exc_info=True)
        return False


def blacklist_access_token(redis_client: redis.Redis, payload: dict) -> None:
    """Đưa 1 access token (đã decode - `payload` từ `get_token_payload`) vào
    Redis blacklist (task 3.3.2, dùng ở `POST /auth/logout`).

    TTL của key Redis = ĐÚNG bằng thời gian còn lại tới lúc token hết hạn tự
    nhiên (`exp` trong payload, Unix timestamp) - KHÔNG lưu lâu hơn cần
    thiết: token hết hạn tự nhiên thì entry Redis cũng tự biến mất cùng lúc
    (Redis tự xóa key hết TTL), không cần dọn tay/cron job riêng.

    FAIL-OPEN nếu Redis lỗi lúc SET (nhất quán với `is_token_blacklisted`,
    cùng lý do): KHÔNG raise lỗi ra ngoài, chỉ log warning - vẫn coi logout
    là THÀNH CÔNG với client (client tự xóa token phía mình, xem
    `frontend/lib/auth.ts`, đó mới là điều quan trọng nhất với UX đăng xuất
    bình thường) - blacklist Redis là lớp phòng thủ THÊM (chặn sớm nếu ai đó
    cố dùng lại token cũ), không phải điều kiện bắt buộc để logout "thành
    công" về mặt người dùng.
    """
    jti = payload.get("jti")
    if not jti:
        return

    exp = payload.get("exp", 0)
    ttl_seconds = int(exp - datetime.now(timezone.utc).timestamp())
    if ttl_seconds <= 0:
        return

    try:
        redis_client.set(_blacklist_key(jti), "1", ex=ttl_seconds)
    except redis.RedisError:
        logger.warning("Redis lỗi lúc blacklist token lúc logout (jti=%s) - bỏ qua, vẫn coi logout thành công", jti, exc_info=True)


def get_token_payload(token: Annotated[str | None, Depends(oauth2_scheme)]) -> dict:
    """Decode + verify chữ ký/hạn access token JWT - CHỈ vậy, KHÔNG check
    blacklist hay load User (đó là get_current_user, dùng dependency này bên
    trong). Tách riêng để endpoint nào cần đọc thông tin token thô (VD
    `POST /auth/logout` cần `jti`/`exp` để blacklist chính token đang dùng)
    có thể dùng trực tiếp, không phải decode token 2 lần - FastAPI tự cache
    kết quả dependency theo request, `get_current_user` VÀ route handler
    cùng khai báo `Depends(get_token_payload)` trong 1 request chỉ chạy hàm
    này ĐÚNG 1 LẦN.
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

    return payload


def get_current_user(
    payload: Annotated[dict, Depends(get_token_payload)],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> User:
    """Từ payload đã decode (get_token_payload): check blacklist (Redis, task
    3.3.2), load User (MySQL) tương ứng.

    Trả về ORM model (không phải Pydantic schema) vì:
    - Route/service layer sau này (Order, Cart...) sẽ cần current_user.id để
      filter dữ liệu theo chủ sở hữu - dùng thẳng model tránh phải query lại.
    - Nhất quán với app/services/auth_service.py (cũng trả về User model).
    - Session từ get_db() còn mở xuyên suốt request nên không có rủi ro
      DetachedInstanceError khi đọc field trong route handler.
    """
    jti = payload.get("jti")
    if jti and is_token_blacklisted(redis_client, jti):
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
    """Tạo access token JWT (thời hạn ngắn, settings.ACCESS_TOKEN_EXPIRE_MINUTES).

    "jti" (JWT ID, uuid4 - task 3.3.2): định danh DUY NHẤT cho từng token phát
    ra (kể cả 2 token tạo cùng lúc cho cùng 1 user cũng có jti khác nhau) -
    dùng để blacklist ĐÚNG 1 token cụ thể lúc logout mà không ảnh hưởng các
    token khác của cùng user (VD user đăng nhập trên 2 thiết bị, logout ở 1
    thiết bị không nên tự động logout luôn thiết bị kia). Xem
    `_blacklist_key`/`is_token_blacklisted` để biết lý do dùng jti thay vì
    blacklist nguyên chuỗi token.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Tạo refresh token JWT (thời hạn dài, settings.REFRESH_TOKEN_EXPIRE_DAYS).

    Cũng có "jti" riêng (task 3.3.2, cùng lý do với access token) - CHƯA có
    cơ chế blacklist/revoke áp dụng cho refresh token ở task này (xem
    docs/KNOWN_TODOS.md) - để sẵn field này ngay từ bây giờ để không phải sửa
    lại cấu trúc payload (và không phải đổi lại mọi token đã phát hành) khi
    task sau thật sự cần revoke refresh token.

    TODO (task sau): endpoint /auth/refresh decode + verify token này
    (claim "type": "refresh") để cấp access token mới; hiện /auth/refresh vẫn
    là placeholder 501.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
