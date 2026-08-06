"""SQLAlchemy model: Category (MySQL).

Bảng `categories` — chi tiết cột/ràng buộc/index xem docs/DATABASE_SCHEMA.md
(task 3.1.1 ERD, 3.1.2 model). File này là nguồn code chính thức; nếu chỉnh
sửa, đồng bộ lại tài liệu đó.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    slug: Mapped[str] = mapped_column(String(150), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Self-reference (danh mục cha) - nullable (danh mục gốc không có cha).
    # KHÔNG khai báo ondelete: DBML (`Ref: > categories.id`) không có annotation
    # `[delete: ...]` cho quan hệ này -> giữ hành vi mặc định của MySQL (NO
    # ACTION/RESTRICT ngầm định) thay vì tự suy đoán CASCADE hay SET NULL.
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
