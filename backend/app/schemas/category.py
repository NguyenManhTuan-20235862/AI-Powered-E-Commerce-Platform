"""Pydantic schemas: Category (request & response models).

TODO (Thành viên A - module Product, task 3.4): hoàn thiện field thật.
"""

from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class CategoryRead(BaseModel):
    id: str
    name: str
    description: str | None = None
