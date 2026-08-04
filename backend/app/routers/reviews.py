"""Router: Review (đánh giá sản phẩm, MongoDB).

TODO (Thành viên A): tạo/đọc review theo product_id, lưu trong MongoDB.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Route kiểm tra router Reviews đã được include đúng."""
    return {"module": "reviews", "status": "ok"}
