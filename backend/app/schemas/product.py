"""Pydantic schemas: Product (request & response models).

TODO (Thành viên A - module Product, task 3.4): hoàn thiện field thật.
"""

from pydantic import BaseModel


class ProductBase(BaseModel):
    name: str
    description: str | None = None
    price: float
    stock: int = 0
    category_id: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    stock: int | None = None
    category_id: str | None = None


class ProductRead(ProductBase):
    id: str
    image_url: str | None = None


class ProductImageRead(BaseModel):
    image_url: str
