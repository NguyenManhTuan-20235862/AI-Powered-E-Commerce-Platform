"""Pydantic schemas: Category (request & response models).

Viết lại HOÀN TOÀN `CategoryCreate`/`CategoryUpdate`/`CategoryRead` (CRUD
Category Admin) - bản trước đó thiếu `slug` (dù model bắt buộc NOT NULL
UNIQUE, xem app/models/category.py) và `parent_id`/`created_at` trong
`CategoryRead`. `CategoryRead` giữ NGUYÊN kế thừa `BaseSchema` (đã sửa đúng
task 4.2.1, xem `docs/KNOWN_TODOS.md` #14 - cùng loại lỗi đã gặp ở
`ProductRead`).

`parent_id` trả PHẲNG (int | None), KHÔNG lồng object danh mục cha như
`ProductRead.category` (`CategorySummary`) - CRUD Admin chỉ cần biết ID cha
để hiển thị/chọn qua dropdown từ danh sách phẳng `GET /categories` đã có
sẵn, không cần join thêm tên cha vào từng dòng.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    # Optional - nếu không truyền, tự sinh từ `name` (xem
    # app/services/category_service.py:generate_unique_category_slug(), tái
    # sử dụng ĐÚNG product_service.slugify() - KHÔNG viết logic slug riêng).
    slug: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    parent_id: int | None = None


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    """Toàn bộ field optional (partial update, field không truyền = giữ
    nguyên - dùng `exclude_unset=True`, cùng pattern `ProductUpdate`).
    Truyền tường minh `parent_id: null` = bỏ danh mục cha (chuyển về gốc),
    KHÁC với không truyền field này (giữ nguyên `parent_id` cũ)."""

    name: str | None = Field(default=None, min_length=1, max_length=150)
    slug: str | None = Field(default=None, max_length=150)
    description: str | None = Field(default=None, max_length=500)
    parent_id: int | None = None


class CategoryRead(BaseSchema):
    id: int
    name: str
    slug: str
    description: str | None = None
    parent_id: int | None = None
    created_at: datetime
