"""Pydantic schemas: Order (task 3.4.2) - viết lại hoàn toàn từ placeholder
cũ, khớp model `Order`/`OrderItem` thật (task 3.1.3)."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.order import OrderStatus
from app.schemas.base import BaseSchema


class OrderCreate(BaseModel):
    """`shipping_address`/`shipping_phone` BẮT BUỘC (khớp NOT NULL ở model) -
    CỐ TÌNH không tự điền từ `users.address`/`users.phone` phía server: đúng
    thiết kế "snapshot lúc đặt" đã ghi ở docs/DATABASE_SCHEMA.md (mục
    `orders`) - giá trị PHẢI đến từ chính request checkout (client tự
    prefill từ profile ở UI nếu muốn, đó là việc của Frontend, không phải
    Backend ngầm suy ra)."""

    shipping_name: str = Field(min_length=1, max_length=150)
    shipping_address: str = Field(min_length=1, max_length=500)
    shipping_phone: str = Field(min_length=1, max_length=20)
    note: str | None = Field(default=None, max_length=500)


class OrderItemRead(BaseSchema):
    """Snapshot BẤT BIẾN tại thời điểm mua - CỐ TÌNH KHÔNG join dữ liệu sản
    phẩm hiện tại (giá/tên sản phẩm có thể đã đổi từ lúc mua) - đúng thiết kế
    `order_items` (xem `app/models/order.py`)."""

    id: int
    product_id: int
    product_name: str
    quantity: int
    price_at_purchase: Decimal


class OrderRead(BaseSchema):
    id: int
    user_id: int
    status: OrderStatus
    total_amount: Decimal
    shipping_name: str
    shipping_address: str
    shipping_phone: str
    note: str | None = None
    items: list[OrderItemRead] = []
    created_at: datetime
    updated_at: datetime


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderListFilter(BaseModel):
    """Query param cho `GET /orders/admin` (task 3.4.2) - filter theo trạng
    thái/khoảng ngày đặt hàng, theo đúng mô tả docs/API_SPEC.md mục 5."""

    status: OrderStatus | None = None
    date_from: date | None = None
    date_to: date | None = None
