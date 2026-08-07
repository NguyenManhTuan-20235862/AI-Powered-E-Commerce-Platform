"""SQLAlchemy model: Product (MySQL).

Bảng `products` — chi tiết cột/ràng buộc/index xem docs/DATABASE_SCHEMA.md
(task 3.1.1 ERD, 3.1.2 model). File này là nguồn code chính thức; nếu chỉnh
sửa, đồng bộ lại tài liệu đó.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # KHÔNG khai báo ondelete: DBML (`Ref: products.category_id > categories.id`)
    # không có annotation `[delete: ...]` -> giữ mặc định NO ACTION, giống
    # Category.parent_id (xem app/models/category.py).
    category_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("categories.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # CHECK (stock_quantity >= 0): CỐ TÌNH KHÔNG khai báo CheckConstraint ở đây
    # - theo đúng DBML (note "CHECK ... thêm bằng migration riêng, DBML không
    # hỗ trợ CHECK") - sẽ thêm bằng migration Alembic riêng ở task 3.1.4, không
    # để autogenerate tự sinh từ model này. SELECT FOR UPDATE lúc checkout (khóa
    # dòng, tránh 2 request trừ kho cùng lúc dẫn tới âm kho) - task 8.2.
    stock_quantity: Mapped[int] = mapped_column(
        Integer, default=0, server_default=text("0"), nullable=False
    )
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # is_active=False: ẩn sản phẩm khỏi catalog thay vì xóa cứng - giữ toàn vẹn
    # lịch sử order_items (order_items.product_id vẫn tham chiếu được, xem
    # app/models/order.py) dù sản phẩm không còn bán.
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        onupdate=func.now(),
        nullable=False,
    )

    # index=True ở category_id/is_active phía trên đã tạo 2 index đơn - thêm
    # composite index riêng (is_active, category_id) vì query catalog thực tế
    # (GET /products lọc theo category + chỉ hiện sản phẩm đang bán) luôn dùng
    # CẢ 2 điều kiện cùng lúc - composite index phục vụ query đó nhanh hơn 2
    # index đơn riêng lẻ cộng lại (MySQL chỉ dùng được 1 index cho 1 lần quét).
    __table_args__ = (
        Index("ix_products_is_active_category_id", "is_active", "category_id"),
    )
