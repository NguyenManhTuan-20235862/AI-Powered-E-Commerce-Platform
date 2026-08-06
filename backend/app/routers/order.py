"""Router: Order Module (`/orders`).

Khung endpoint theo docs/API_SPEC.md - mục 5.

Lưu ý: route `/orders/admin` được khai báo TRƯỚC `/orders/{order_id}` để tránh
bị route templated nuốt mất (FastAPI khớp route theo thứ tự khai báo).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user
from app.schemas.common import APIResponse, PaginatedData
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["Order"])


@router.post(
    "",
    response_model=APIResponse[OrderRead],
    summary="Tạo đơn hàng từ giỏ hàng",
    status_code=status.HTTP_201_CREATED,
    responses=auth_responses(),
)
def create_order(
    payload: OrderCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[OrderRead]:
    """Tạo đơn hàng từ giỏ hàng (transaction trừ tồn kho, có xử lý race condition). Yêu cầu: Customer."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.get(
    "",
    response_model=APIResponse[PaginatedData[OrderRead]],
    summary="Danh sách đơn hàng của user hiện tại",
    responses=auth_responses(),
)
def list_my_orders(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[PaginatedData[OrderRead]]:
    """Danh sách đơn hàng của user hiện tại. Yêu cầu: Customer."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.get(
    "/admin",
    response_model=APIResponse[PaginatedData[OrderRead]],
    summary="Danh sách toàn bộ đơn hàng (Admin)",
    responses=auth_responses(forbidden=True),
)
def list_all_orders(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[PaginatedData[OrderRead]]:
    """Danh sách toàn bộ đơn hàng (filter theo trạng thái, ngày). Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.get(
    "/{order_id}",
    response_model=APIResponse[OrderRead],
    summary="Chi tiết 1 đơn hàng",
    responses=auth_responses(not_found=True),
)
def get_order(
    order_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[OrderRead]:
    """Chi tiết 1 đơn hàng. Yêu cầu: Customer (chủ đơn), Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.put(
    "/{order_id}/cancel",
    response_model=APIResponse[OrderRead],
    summary="Hủy đơn hàng",
    responses=auth_responses(not_found=True),
)
def cancel_order(
    order_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[OrderRead]:
    """Hủy đơn hàng (nếu đủ điều kiện). Yêu cầu: Customer (chủ đơn)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.put(
    "/{order_id}/status",
    response_model=APIResponse[OrderRead],
    summary="Cập nhật trạng thái đơn hàng",
    responses=auth_responses(forbidden=True, not_found=True),
)
def update_order_status(
    order_id: str,
    payload: OrderStatusUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[OrderRead]:
    """Cập nhật trạng thái đơn hàng (xác nhận, đang giao, đã giao). Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")
