"""Pydantic schemas: Category (request & response models).

`CategoryRead` dùng thật từ task 4.2.1 (`GET /categories`, phục vụ filter
danh mục ở trang catalog sản phẩm) - đã sửa `id: str` (sai, model `Category`
thật dùng `BigInteger`, xem app/models/category.py) thành `int`, và đổi kế
thừa sang `BaseSchema` (không phải `BaseModel` trơ) để có `from_attributes`
- CẦN thiết để `CategoryRead.model_validate(category_orm_object)` đọc được
trực tiếp từ ORM object, giống mọi Read schema khác trong dự án (VD
ProductRead) - lỗi cùng loại với docs/KNOWN_TODOS.md #14.

`CategoryCreate`/`CategoryUpdate`/router POST-PUT-DELETE vẫn CHƯA hoàn
thiện (thiếu `slug` dù model bắt buộc NOT NULL UNIQUE, tương tự
`ProductCreate` cần `slugify()`) - chưa tới task quản lý danh mục Admin.
"""

from pydantic import BaseModel

from app.schemas.base import BaseSchema


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class CategoryRead(BaseSchema):
    id: int
    name: str
    description: str | None = None
