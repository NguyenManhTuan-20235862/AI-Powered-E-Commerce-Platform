"""Router: Product (catalog sản phẩm, MySQL).

TODO (Thành viên A): CRUD sản phẩm, tìm kiếm, phân trang, lọc theo danh mục...
"""

from fastapi import APIRouter

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Route kiểm tra router Products đã được include đúng."""
    return {"module": "products", "status": "ok"}
