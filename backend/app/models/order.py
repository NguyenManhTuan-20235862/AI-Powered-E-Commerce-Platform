"""SQLAlchemy model: Order, OrderItem, Payment (MySQL).

Bảng `orders`, `order_items`, `payments` — chi tiết cột/ràng buộc/index xem
docs/DATABASE_SCHEMA.md (task 3.1.1 ERD, 3.1.3 model). File này là nguồn code
chính thức; nếu chỉnh sửa, đồng bộ lại tài liệu đó.
"""

import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    shipping = "shipping"
    delivered = "delivered"
    cancelled = "cancelled"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    refunded = "refunded"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # ondelete="RESTRICT" - đúng theo DBML (`Ref: orders.user_id > users.id
    # [delete: restrict]`) - KHÁC cart_items (CASCADE): order là dữ liệu lịch
    # sử/nghiệp vụ (hóa đơn, doanh thu), không được xóa theo khi xóa user - phải
    # xử lý nghiệp vụ khác trước (VD: khóa is_active thay vì xóa cứng user, xem
    # app/models/user.py) nếu user đó còn đơn hàng.
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus, native_enum=True, length=20),
        default=OrderStatus.pending,
        server_default=OrderStatus.pending.value,
        nullable=False,
        index=True,
    )
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    shipping_address: Mapped[str] = mapped_column(String(500), nullable=False)
    shipping_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # index=True - phục vụ dashboard doanh thu theo ngày/tuần/tháng (task 5.3),
    # query luôn lọc theo khoảng created_at.
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        onupdate=func.now(),
        nullable=False,
    )


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # ondelete="RESTRICT" - đơn hàng là lịch sử, không tự xóa theo order/product.
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    # KHÔNG index=True riêng - DBML chỉ khai báo index cho order_id (indexes
    # block chỉ có `order_id`) - MySQL/InnoDB vẫn tự tạo index ngầm cho
    # product_id để phục vụ FOREIGN KEY (bắt buộc theo cơ chế InnoDB), không
    # cần khai báo tay thêm.
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    # Snapshot tên sản phẩm lúc mua - phòng khi products.name đổi/xóa sau này,
    # hóa đơn cũ vẫn hiển thị đúng tên tại thời điểm mua, không bị ảnh hưởng
    # bởi thay đổi ở bảng products.
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    # Snapshot giá lúc mua - KHÔNG đổi theo products.price (giá sản phẩm có
    # thể thay đổi sau ngày đặt hàng, hóa đơn phải giữ đúng giá tại thời điểm
    # giao dịch).
    price_at_purchase: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # KHÔNG có updated_at - order_items là bản ghi lịch sử bất biến (immutable
    # snapshot), không có nghiệp vụ "sửa" 1 dòng order_item đã tạo, đúng theo
    # DBML (bảng này không khai báo cột updated_at).
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # unique=True - quan hệ 1-1 với Order, đúng theo DBML dùng "-" (KHÔNG phải
    # ">") ở `Ref: payments.order_id - orders.id [delete: restrict]` - 1 đơn
    # hàng chỉ có đúng 1 bản ghi thanh toán.
    order_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("orders.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    # nullable=True - transaction_id do cổng thanh toán (VNPay/Momo) trả về
    # SAU khi khởi tạo giao dịch, không có sẵn ngay lúc tạo bản ghi payment với
    # status="pending" - đúng theo DBML (field này KHÔNG có `not null`).
    # unique=True - tránh xử lý trùng khi cổng thanh toán gọi callback nhiều
    # lần cho cùng 1 giao dịch (idempotency ở tầng DB, không chỉ ở code).
    transaction_id: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus, native_enum=True, length=20),
        default=PaymentStatus.pending,
        server_default=PaymentStatus.pending.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        onupdate=func.now(),
        nullable=False,
    )
