"""Router: Payment Module (`/payments`) — liên quan task 8.1.

Khung endpoint theo docs/API_SPEC.md - mục 6.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user
from app.schemas.common import APIResponse, MessageResponse
from app.schemas.payment import PaymentCreateRequest, PaymentCreateResponse, PaymentStatusRead

router = APIRouter(prefix="/payments", tags=["Payment"])


@router.post(
    "/create",
    response_model=APIResponse[PaymentCreateResponse],
    summary="Tạo giao dịch thanh toán (VNPay/Momo sandbox)",
    status_code=status.HTTP_201_CREATED,
    responses=auth_responses(),
)
def create_payment(
    payload: PaymentCreateRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[PaymentCreateResponse]:
    """Tạo giao dịch thanh toán (VNPay/Momo sandbox), trả về URL redirect. Yêu cầu: Customer."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 8.1")


@router.get(
    "/callback",
    response_model=MessageResponse,
    summary="Nhận callback/IPN từ cổng thanh toán",
)
def payment_callback() -> MessageResponse:
    """Nhận callback/IPN từ cổng thanh toán, cập nhật trạng thái Order.

    Public - xác thực bằng chữ ký (signature) của cổng thanh toán, không dùng JWT.
    TODO: định dạng response thật phải theo đúng yêu cầu của từng cổng (VNPay/Momo)
    ở task 8.1, có thể không phải JSON như `MessageResponse` này.
    """
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 8.1")


@router.get(
    "/{order_id}/status",
    response_model=APIResponse[PaymentStatusRead],
    summary="Kiểm tra trạng thái thanh toán của 1 đơn hàng",
    responses=auth_responses(not_found=True),
)
def get_payment_status(
    order_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[PaymentStatusRead]:
    """Kiểm tra trạng thái thanh toán của 1 đơn hàng. Yêu cầu: Customer, Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 8.1")
