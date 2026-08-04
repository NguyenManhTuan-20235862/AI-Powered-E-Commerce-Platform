"""Router: Cart (giỏ hàng, MySQL).

TODO (Thành viên A): thêm/xóa/sửa sản phẩm trong giỏ, tính tổng tiền...
"""

from fastapi import APIRouter

router = APIRouter(prefix="/cart", tags=["Cart"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Route kiểm tra router Cart đã được include đúng."""
    return {"module": "cart", "status": "ok"}
