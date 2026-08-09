"""Business logic: Auth (đăng ký, đăng nhập) - tách khỏi router auth.py."""

from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def register_user(db: Session, payload: UserCreate) -> User:
    """Tạo tài khoản mới - LUÔN gán role=customer, không nhận role từ input.

    Caller (router) chịu trách nhiệm kiểm tra email đã tồn tại chưa trước khi
    gọi hàm này (trả 400 ở tầng router theo docs/API_SPEC.md).
    """
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        address=payload.address,
        role=UserRole.customer,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Trả về User nếu email + password đúng, None nếu sai (không phân biệt lý do
    để tránh lộ thông tin email nào đã tồn tại trong hệ thống)."""
    user = get_user_by_email(db, email)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user
