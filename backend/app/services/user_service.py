"""Business logic: User Management cho Admin - tách khỏi router
app/routers/user.py, cùng convention `order_service.py`/`product_service.py`.

Implement khi port trang Quản lý người dùng Admin (Frontend) - trước đó cả
`GET /users`, `GET /users/{id}`, `PUT /users/{id}/status` đều `501`
placeholder (phát hiện lúc bắt đầu port, ngoài phạm vi ban đầu nhưng đã xác
nhận với người dùng để mở rộng - không có API nào để Frontend gọi thật nếu
không làm phần này trước).
"""

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import ChangePasswordRequest, UserResponse, UserUpdate


class UserServiceError(Exception):
    """Lỗi nghiệp vụ User (mật khẩu cũ không đúng...) - router dịch sang
    HTTPException 400, cùng convention `CartError` (`cart_service.py`)."""


def list_users(
    db: Session,
    *,
    page: int,
    page_size: int,
    role: UserRole | None,
    is_active: bool | None,
    search: str | None,
) -> tuple[list[UserResponse], int]:
    """`search` khớp `full_name` HOẶC `email` (ilike, không phân biệt hoa/
    thường) - cùng tinh thần ô tìm kiếm gộp chung đã dùng ở
    `order_service.list_orders()` (task 4.4.2), khác ở chỗ user không có
    field dạng "mã" số như đơn hàng nên chỉ cần so khớp text, không cần tách
    nhánh parse số riêng."""
    query = db.query(User)
    if role is not None:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(User.full_name.ilike(pattern), User.email.ilike(pattern)))

    total = query.count()
    users = query.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return [UserResponse.model_validate(u) for u in users], total


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def update_user_status(db: Session, user: User, is_active: bool) -> None:
    """Khóa/mở khóa tài khoản - CHỈ đổi `is_active`, không có logic phụ nào
    khác (không tự blacklist token đang dùng của user đó - chấp nhận độ trễ
    tới khi token access hiện tại hết hạn tự nhiên, cùng mức độ đơn giản đã
    chọn cho các quyết định khác trong dự án; `POST /auth/login` đã tự chặn
    đăng nhập MỚI ngay khi `is_active=False`, xem app/routers/auth.py)."""
    user.is_active = is_active
    db.commit()
    db.refresh(user)


def update_profile(db: Session, user: User, payload: UserUpdate) -> User:
    """Cập nhật thông tin cá nhân (`PUT /users/me`) - CHỈ ghi đè field client
    THỰC SỰ gửi lên (`model_dump(exclude_unset=True)`) - field không gửi giữ
    nguyên giá trị cũ, không bị ép về `None` (toàn bộ field `UserUpdate` đều
    optional, gửi thiếu 1 field không có nghĩa là muốn xóa field đó)."""
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def change_password(db: Session, user: User, payload: ChangePasswordRequest) -> None:
    """Đổi mật khẩu (`PUT /users/me/password`) - PHẢI xác nhận đúng mật khẩu
    CŨ trước khi cho đổi (chặn kẻ chiếm được access token ngắn hạn tự đổi mật
    khẩu chiếm quyền dài hạn tài khoản)."""
    if not verify_password(payload.old_password, user.password_hash):
        raise UserServiceError("Mật khẩu cũ không đúng")
    user.password_hash = hash_password(payload.new_password)
    db.commit()
