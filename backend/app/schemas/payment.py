"""Pydantic schemas: Payment (request & response models).

TODO (Thành viên A - task 8.1): hoàn thiện field thật theo API của VNPay/Momo.
"""

from pydantic import BaseModel


class PaymentCreateRequest(BaseModel):
    order_id: str
    provider: str = "vnpay"


class PaymentCreateResponse(BaseModel):
    payment_url: str
    order_id: str


class PaymentStatusRead(BaseModel):
    order_id: str
    status: str
