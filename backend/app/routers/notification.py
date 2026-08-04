"""Router: Notification / Realtime Module (SSE).

Khung endpoint theo docs/API_SPEC.md - mục 9. Logic SSE thật (StreamingResponse
với media_type="text/event-stream") sẽ implement ở task 9.x.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notification"])


@router.get(
    "/orders/stream",
    summary="Stream sự kiện cập nhật trạng thái đơn hàng realtime (SSE)",
    responses=auth_responses(),
)
def stream_order_updates(current_user: Annotated[dict, Depends(get_current_user)]) -> None:
    """Stream sự kiện cập nhật trạng thái đơn hàng realtime (SSE). Yêu cầu: Customer.

    TODO: implement thật bằng StreamingResponse ở task 9.x.
    """
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 9.x")


@router.get(
    "/admin/stream",
    summary="Stream sự kiện đơn hàng mới, thống kê realtime cho Admin (SSE)",
    responses=auth_responses(forbidden=True),
)
def stream_admin_events(current_user: Annotated[dict, Depends(get_current_user)]) -> None:
    """Stream sự kiện đơn hàng mới, thống kê realtime cho Admin (SSE). Yêu cầu: Admin.

    TODO: implement thật bằng StreamingResponse ở task 9.x.
    """
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 9.x")
