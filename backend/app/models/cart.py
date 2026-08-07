"""SQLAlchemy model: CartItem (MySQL).

Bảng `cart_items` — chi tiết cột/ràng buộc/index xem docs/DATABASE_SCHEMA.md
(task 3.1.1 ERD, 3.1.3 model). File này là nguồn code chính thức; nếu chỉnh
sửa, đồng bộ lại tài liệu đó.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # ondelete="CASCADE" (user_id, product_id): đúng theo DBML
    # (`Ref: cart_items.user_id > users.id [delete: cascade]` và tương tự cho
    # product_id) - xóa user hoặc xóa product thì giỏ hàng liên quan tự xóa
    # theo, hợp lý vì cart_items chỉ là trạng thái tạm thời, không phải dữ liệu
    # lịch sử cần giữ lại (khác order_items - xem app/models/order.py, dùng
    # RESTRICT vì là lịch sử đơn hàng).
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        onupdate=func.now(),
        nullable=False,
    )

    # UNIQUE (user_id, product_id) - 1 user không có 2 dòng cùng 1 sản phẩm
    # (thêm sản phẩm đã có trong giỏ -> tăng quantity dòng cũ ở tầng service,
    # không insert dòng mới). Đây là index DUY NHẤT khai báo cho bảng này theo
    # DBML (không có index đơn riêng cho user_id/product_id) - MySQL/InnoDB tự
    # tạo index ngầm cho product_id để phục vụ FOREIGN KEY (bắt buộc theo cơ
    # chế InnoDB, không cần khai báo tay); user_id đã được phủ bởi vị trí đầu
    # tiên (leftmost prefix) của unique index composite dưới đây, không cần
    # index đơn riêng.
    __table_args__ = (
        UniqueConstraint("user_id", "product_id", name="uq_cart_items_user_id_product_id"),
    )
