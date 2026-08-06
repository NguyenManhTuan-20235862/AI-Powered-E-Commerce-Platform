"""Router: Order Module (`/orders`).

Khung endpoint theo docs/API_SPEC.md - mục 5.

Lưu ý: route `/orders/admin` được khai báo TRƯỚC `/orders/{order_id}` để tránh
bị route templated nuốt mất (FastAPI khớp route theo thứ tự khai báo).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, PaginatedResponse
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate

router = APIRouter(prefix="/orders", tags=["Order"])


@router.post(
    "",
    response_model=APIResponse[OrderRead],
    summary="Tạo đơn hàng từ giỏ hàng",
    status_code=status.HTTP_201_CREATED,
    responses=auth_responses(forbidden=True),
)
def create_order(
    payload: OrderCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
) -> APIResponse[OrderRead]:
    """Tạo đơn hàng từ giỏ hàng (transaction trừ tồn kho, có xử lý race condition). Yêu cầu: Customer."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.get(
    "",
    response_model=APIResponse[PaginatedResponse[OrderRead]],
    summary="Danh sách đơn hàng của user hiện tại",
    responses=auth_responses(forbidden=True),
)
def list_my_orders(
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
) -> APIResponse[PaginatedResponse[OrderRead]]:
    """Danh sách đơn hàng của user hiện tại. Yêu cầu: Customer."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.get(
    "/admin",
    response_model=APIResponse[PaginatedResponse[OrderRead]],
    summary="Danh sách toàn bộ đơn hàng (Admin)",
    responses=auth_responses(forbidden=True),
)
def list_all_orders(
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> APIResponse[PaginatedResponse[OrderRead]]:
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
    current_user: Annotated[User, Depends(get_current_user)],
) -> APIResponse[OrderRead]:
    """Chi tiết 1 đơn hàng. Yêu cầu: Customer (chủ đơn), Admin.

    Cả 2 role hiện có (customer, admin) đều được vào - không dùng require_role()
    vì role không đủ để quyết định quyền truy cập ở đây; còn cần kiểm tra
    order.user_id == current_user.id cho Customer (Admin luôn được xem mọi đơn).
    TODO (task 3.4 - business logic thật): thêm check "chủ đơn" trong hàm này,
    trả 403 nếu current_user là customer nhưng không phải chủ đơn.
    """
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.put(
    "/{order_id}/cancel",
    response_model=APIResponse[OrderRead],
    summary="Hủy đơn hàng",
    responses=auth_responses(forbidden=True, not_found=True),
)
def cancel_order(
    order_id: str,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
) -> APIResponse[OrderRead]:
    """Hủy đơn hàng (nếu đủ điều kiện). Yêu cầu: Customer (chủ đơn).

    TODO (task 3.4 - business logic thật): kiểm tra order.user_id == current_user.id
    (require_role() chỉ đảm bảo đúng role, chưa đảm bảo đúng chủ đơn).
    """
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
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> APIResponse[OrderRead]:
    """Cập nhật trạng thái đơn hàng (xác nhận, đang giao, đã giao). Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")
