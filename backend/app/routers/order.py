"""Router: Order Module (`/orders`, task 3.4.2).

Khung endpoint theo docs/API_SPEC.md - mục 5.

Lưu ý: route `/orders/admin` được khai báo TRƯỚC `/orders/{order_id}` để tránh
bị route templated nuốt mất (FastAPI khớp route theo thứ tự khai báo).
"""

from datetime import date
from typing import Annotated

import redis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.cache import invalidate_by_prefix
from app.core.database import get_db, get_redis
from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user, require_role
from app.models.order import OrderStatus
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, PaginatedResponse, PaginationParams, paginated_response, success_response
from app.schemas.order import OrderCreate, OrderRead, OrderStatusUpdate
from app.services import order_service
from app.services.notification_service import publish_order_status_update
from app.services.product_service import PRODUCT_LIST_CACHE_PREFIX

router = APIRouter(prefix="/orders", tags=["Order"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng")


def _forbidden_not_owner() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền truy cập đơn hàng này")


@router.post(
    "",
    response_model=APIResponse[OrderRead],
    summary="Tạo đơn hàng từ giỏ hàng",
    status_code=status.HTTP_201_CREATED,
    responses={**auth_responses(forbidden=True), 409: {"description": "Giỏ hàng trống hoặc không đủ tồn kho"}},
)
def create_order(
    payload: OrderCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> APIResponse[OrderRead]:
    """Tạo đơn hàng từ giỏ hàng (transaction trừ tồn kho, `SELECT ... FOR
    UPDATE` thật - xem `app/services/order_service.py`). Yêu cầu: Customer.

    409 (không phải 400) khi thiếu tồn kho - đây là XUNG ĐỘT trạng thái
    (dữ liệu đã đổi giữa lúc thêm vào giỏ và lúc đặt hàng), đúng ngữ nghĩa
    HTTP 409 hơn 400 (lỗi định dạng request).
    """
    try:
        order = order_service.checkout(db, current_user, payload)
    except order_service.CheckoutError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    # stock_quantity của (có thể nhiều) sản phẩm vừa đổi - invalidate cache
    # danh sách sản phẩm (task 3.4.1) để GET /products phản ánh đúng ngay.
    invalidate_by_prefix(redis_client, PRODUCT_LIST_CACHE_PREFIX)
    return success_response(data=order_service.to_order_read_single(db, order), message="Đặt hàng thành công")


@router.get(
    "",
    response_model=APIResponse[PaginatedResponse[OrderRead]],
    summary="Danh sách đơn hàng của user hiện tại",
    responses=auth_responses(forbidden=True),
)
def list_my_orders(
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
    # alias="status" - cùng lý do list_all_orders() bên dưới (tên query param
    # tự nhiên cho client, tên Python tránh che module fastapi.status). Thêm
    # task 4.3.3 - phục vụ tab lọc trạng thái ở trang lịch sử đơn hàng.
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
) -> APIResponse[PaginatedResponse[OrderRead]]:
    """Danh sách đơn hàng của user hiện tại, lọc được theo trạng thái qua
    `?status=`. Yêu cầu: Customer."""
    items, total = order_service.list_orders(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        user_id=current_user.id,
        status_filter=status_filter,
        date_from=None,
        date_to=None,
    )
    return success_response(data=paginated_response(items, total, pagination.page, pagination.page_size))


@router.get(
    "/admin",
    response_model=APIResponse[PaginatedResponse[OrderRead]],
    summary="Danh sách toàn bộ đơn hàng (Admin)",
    responses=auth_responses(forbidden=True),
)
def list_all_orders(
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
    # alias="status" - tên query param tự nhiên cho client (?status=pending),
    # tên Python `status_filter` để KHÔNG che (shadow) module `fastapi.status`
    # (đã import, dùng cho HTTP status code ở các endpoint khác trong file này).
    status_filter: Annotated[OrderStatus | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    # task 4.4.2 - tìm theo "mã đơn hàng" (thực chất là `id` số, hệ thống
    # không có mã dạng chữ, xem docstring `order_service.list_orders()`) hoặc
    # theo tên khách hàng (`shipping_name`) - dùng chung 1 ô search ở UI.
    search: str | None = None,
) -> APIResponse[PaginatedResponse[OrderRead]]:
    """Danh sách toàn bộ đơn hàng (filter theo trạng thái, ngày, tìm theo mã
    đơn/tên khách hàng qua `?search=`). Yêu cầu: Admin."""
    items, total = order_service.list_orders(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        user_id=None,
        status_filter=status_filter,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return success_response(data=paginated_response(items, total, pagination.page, pagination.page_size))


@router.get(
    "/{order_id}",
    response_model=APIResponse[OrderRead],
    summary="Chi tiết 1 đơn hàng",
    responses=auth_responses(forbidden=True, not_found=True),
)
def get_order(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> APIResponse[OrderRead]:
    """Chi tiết 1 đơn hàng. Yêu cầu: Customer (chủ đơn), Admin.

    Không dùng `require_role()` vì role không đủ để quyết định quyền truy
    cập - Customer CHỈ xem được đơn CỦA CHÍNH HỌ (`order.user_id ==
    current_user.id`), Admin luôn được xem mọi đơn - check ownership tường
    minh bên dưới (task 3.4.2, xử lý dứt điểm TODO đã note từ task 1.3.3,
    xem docs/KNOWN_TODOS.md #1).
    """
    order = order_service.get_order_by_id(db, order_id)
    if order is None:
        raise _not_found()
    if current_user.role != UserRole.admin and order.user_id != current_user.id:
        raise _forbidden_not_owner()

    return success_response(data=order_service.to_order_read_single(db, order))


@router.put(
    "/{order_id}/cancel",
    response_model=APIResponse[OrderRead],
    summary="Hủy đơn hàng",
    responses={
        **auth_responses(forbidden=True, not_found=True),
        400: {"description": "Đơn hàng không ở trạng thái cho phép hủy"},
    },
)
def cancel_order(
    order_id: int,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> APIResponse[OrderRead]:
    """Hủy đơn hàng (chỉ khi còn "pending", hoàn lại tồn kho - xem
    `app/services/order_service.py:cancel_order`). Yêu cầu: Customer (chủ đơn).

    Check ownership tường minh (task 3.4.2, xử lý dứt điểm TODO đã note từ
    task 1.3.3, xem docs/KNOWN_TODOS.md #1) - `require_role()` CHỈ đảm bảo
    đúng role (Customer), CHƯA đảm bảo đúng chủ đơn (1 Customer bất kỳ có thể
    đoán `order_id` của người khác nếu không check).
    """
    order = order_service.get_order_by_id(db, order_id)
    if order is None:
        raise _not_found()
    if order.user_id != current_user.id:
        raise _forbidden_not_owner()

    try:
        order_service.cancel_order(db, order)
    except order_service.CancelNotAllowedError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    invalidate_by_prefix(redis_client, PRODUCT_LIST_CACHE_PREFIX)  # đã hoàn kho
    return success_response(data=order_service.to_order_read_single(db, order), message="Đã hủy đơn hàng")


@router.put(
    "/{order_id}/status",
    response_model=APIResponse[OrderRead],
    summary="Cập nhật trạng thái đơn hàng",
    responses={
        **auth_responses(forbidden=True, not_found=True),
        400: {"description": "Chuyển trạng thái không hợp lệ (sai state machine)"},
    },
)
def update_order_status(
    order_id: int,
    payload: OrderStatusUpdate,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> APIResponse[OrderRead]:
    """Cập nhật trạng thái đơn hàng (xác nhận, đang giao, đã giao...). Yêu
    cầu: Admin. Chỉ chấp nhận transition hợp lệ theo state machine cơ bản
    (`order_service.VALID_STATUS_TRANSITIONS`) - 400 nếu sai quy tắc (VD
    "pending" nhảy thẳng sang "delivered", hoặc đổi tiếp từ trạng thái cuối
    "delivered"/"cancelled"). Đổi sang "cancelled" qua đây CŨNG hoàn kho,
    giống `PUT /orders/{id}/cancel` (nhất quán, xem
    `app/services/order_service.py:update_order_status`)."""
    order = order_service.get_order_by_id(db, order_id)
    if order is None:
        raise _not_found()

    try:
        order_service.update_order_status(db, order, payload.status)
    except order_service.InvalidStatusTransitionError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    invalidate_by_prefix(redis_client, PRODUCT_LIST_CACHE_PREFIX)
    # PUBLISH cho SSE (task 5.2.1) - CHỈ tới đây khi update_order_status() ở
    # trên đã db.commit() thành công (không rơi vào nhánh except) - không
    # publish sự kiện cho 1 lần đổi trạng thái thất bại.
    publish_order_status_update(redis_client, user_id=order.user_id, order_id=order.id, new_status=order.status)
    return success_response(data=order_service.to_order_read_single(db, order), message="Đã cập nhật trạng thái đơn hàng")
