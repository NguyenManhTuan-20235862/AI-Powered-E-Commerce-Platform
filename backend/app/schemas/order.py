"""Pydantic schemas: Order (request & response models).

TODO (Thành viên A - module Order): hoàn thiện field thật (địa chỉ giao hàng,
phương thức thanh toán...) ở task 3.4 / 8.x.
"""

from pydantic import BaseModel


class OrderCreate(BaseModel):
    shipping_address: str | None = None
    note: str | None = None


class OrderItemRead(BaseModel):
    product_id: str
    product_name: str
    quantity: int
    price: float


class OrderRead(BaseModel):
    id: str
    status: str
    total: float
    items: list[OrderItemRead] = []


class OrderStatusUpdate(BaseModel):
    status: str
