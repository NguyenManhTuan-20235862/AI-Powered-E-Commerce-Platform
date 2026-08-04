"""Router: Order (đơn hàng, MySQL) + SSE trạng thái đơn hàng.

TODO (Thành viên A):
- CRUD đơn hàng, checkout từ giỏ hàng
- Endpoint SSE /orders/{id}/status-stream để đẩy trạng thái đơn hàng real-time
"""

from fastapi import APIRouter

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Route kiểm tra router Orders đã được include đúng."""
    return {"module": "orders", "status": "ok"}
