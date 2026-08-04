"""Pydantic schemas: Cart (request & response models).

TODO (Thành viên A - module Cart): hoàn thiện field thật.
"""

from pydantic import BaseModel, Field


class CartItemCreate(BaseModel):
    product_id: str
    quantity: int = Field(default=1, ge=1)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1)


class CartItemRead(BaseModel):
    id: str
    product_id: str
    product_name: str
    quantity: int
    price: float


class CartRead(BaseModel):
    items: list[CartItemRead] = []
    total: float = 0
