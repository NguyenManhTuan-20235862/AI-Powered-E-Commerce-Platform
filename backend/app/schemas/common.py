"""Schema dùng chung: envelope response chuẩn theo docs/API_SPEC.md.

Toàn bộ response JSON thành công của API được bọc trong
`{ "success": bool, "data": ..., "message": str }`.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Envelope chuẩn cho response thành công có kèm dữ liệu."""

    success: bool = True
    data: T | None = None
    message: str = ""


class MessageResponse(BaseModel):
    """Response cho các action không trả về dữ liệu cụ thể (VD: logout, xóa)."""

    success: bool = True
    message: str = ""


class PaginatedData(BaseModel, Generic[T]):
    """Payload phân trang - đặt trong field `data` của APIResponse."""

    items: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
