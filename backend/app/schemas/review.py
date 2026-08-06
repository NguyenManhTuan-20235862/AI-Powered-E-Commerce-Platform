"""Pydantic schemas: Review (request & response models, lưu ở MongoDB).

TODO (Thành viên A - module Review): hoàn thiện field thật.
"""

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = None


class ReviewRead(BaseModel):
    id: str
    product_id: str
    user_id: str
    rating: int
    comment: str | None = None
