"""Pydantic schemas: Payment (VNPay sandbox thật, task "Quyết định và hoàn
thiện thanh toán") - viết lại HOÀN TOÀN từ placeholder cũ task 8.1
(`PaymentCreateRequest.order_id: str` sai kiểu - `orders.id` là `BigInteger`,
cùng loại lỗi đã sửa cho `ProductRead`/`TopProductRead`, xem
docs/KNOWN_TODOS.md #14).
"""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.order import PaymentStatus
from app.schemas.base import BaseSchema


class PaymentCreateRequest(BaseModel):
    order_id: int


class PaymentCreateResponse(BaseModel):
    payment_id: int
    order_id: int
    payment_url: str


class PaymentStatusRead(BaseSchema):
    order_id: int
    payment_method: str
    transaction_id: str | None
    amount: Decimal
    status: PaymentStatus
    created_at: datetime
    updated_at: datetime
