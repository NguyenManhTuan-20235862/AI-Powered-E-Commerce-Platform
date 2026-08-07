"""Schema dùng chung: envelope response chuẩn theo docs/API_SPEC.md (task 1.4.1).

Toàn bộ response JSON của API được bọc trong
`{ "success": bool, "data": ..., "message": str }`.
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.schemas.base import BaseSchema

T = TypeVar("T")


class APIResponse(BaseSchema, Generic[T]):
    """Envelope chuẩn cho response thành công có kèm dữ liệu."""

    success: bool = True
    data: T | None = None
    message: str = ""


class MessageResponse(BaseSchema):
    """Response cho các action không trả về dữ liệu cụ thể (VD: logout, xóa)."""

    success: bool = True
    message: str = ""


class ErrorResponse(BaseSchema):
    """Envelope chuẩn cho response lỗi (400/401/403/404/429...).

    Được app/main.py dùng làm hình dạng thật của mọi lỗi qua exception handler
    chung cho HTTPException - raise HTTPException(status_code=..., detail=...)
    ở router như bình thường, KHÔNG cần tự tạo ErrorResponse thủ công; handler
    sẽ tự chuyển `detail` thành `message` và bọc đúng envelope này.
    """

    success: bool = False
    data: None = None
    message: str
    error_code: str | None = None


class PaginationParams(BaseModel):
    """Query param chung cho các endpoint danh sách (GET /products, /orders...).

    Không kế thừa BaseSchema - đây là input parse từ query string, không phải
    output đọc từ ORM nên không cần from_attributes.
    """

    page: int = Field(default=1, ge=1, description="Trang hiện tại, bắt đầu từ 1")
    page_size: int = Field(default=20, ge=1, le=100, description="Số item mỗi trang, tối đa 100")


class PaginatedResponse(BaseSchema, Generic[T]):
    """Payload phân trang - đặt trong field `data` của APIResponse.

    VD: APIResponse[PaginatedResponse[ProductRead]] cho GET /products.
    """

    items: list[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 0


def success_response(data: T | None = None, message: str = "Thành công") -> APIResponse[T]:
    """Tạo APIResponse thành công - gọi trong router thay vì tự `APIResponse(...)`.

        return success_response(data=UserResponse.model_validate(user))
    """
    return APIResponse(success=True, data=data, message=message)


def paginated_response(
    items: list[T],
    total: int,
    page: int,
    page_size: int,
) -> PaginatedResponse[T]:
    """Tạo PaginatedResponse, tự tính `total_pages` từ total/page_size.

        return success_response(data=paginated_response(items, total, page, page_size))
    """
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size, total_pages=total_pages)
