"""SQLAlchemy model: User (MySQL).

Bảng `users` — chi tiết cột/ràng buộc/index xem docs/DATABASE_SCHEMA.md (task
1.3.1). File này là nguồn code chính thức; nếu chỉnh sửa, đồng bộ lại tài liệu đó.
"""

import enum
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, String, func, text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(str, enum.Enum):
    customer = "customer"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=True, length=20),
        default=UserRole.customer,
        server_default=UserRole.customer.value,
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    # server_default dùng raw SQL "ON UPDATE CURRENT_TIMESTAMP" (cú pháp riêng của
    # MySQL) để DB tự cập nhật cột này ngay cả khi có UPDATE bằng SQL thô, không
    # đi qua SQLAlchemy. onupdate=func.now() giữ lại để ORM cũng set giá trị ngay
    # trong câu UPDATE (không phải đợi round-trip đọc lại từ DB).
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        onupdate=func.now(),
        nullable=False,
    )
