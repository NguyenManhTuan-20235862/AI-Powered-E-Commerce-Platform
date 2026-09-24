"""Router: Payment Module (`/payments`) - VNPay sandbox THẬT (task "Quyết
định và hoàn thiện thanh toán", thay 3 endpoint `501` cũ task 8.1).

Khung endpoint theo docs/API_SPEC.md - mục 6. Chi tiết thiết kế/quyết định
kiến trúc xem docstring `app/services/payment_service.py`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, success_response
from app.schemas.payment import PaymentCreateRequest, PaymentCreateResponse, PaymentStatusRead
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["Payment"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy đơn hàng")


def _forbidden_not_owner() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không có quyền truy cập đơn hàng này")


@router.post(
    "/create",
    response_model=APIResponse[PaymentCreateResponse],
    summary="Tạo giao dịch thanh toán VNPay",
    status_code=status.HTTP_201_CREATED,
    responses={
        **auth_responses(forbidden=True, not_found=True),
        400: {"description": "Đơn hàng đã hủy"},
        409: {"description": "Đơn hàng đã thanh toán/hoàn tiền, không thể tạo giao dịch mới"},
        503: {"description": "Cổng thanh toán VNPay chưa được cấu hình"},
    },
)
def create_payment(
    payload: PaymentCreateRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
    db: Annotated[Session, Depends(get_db)],
) -> APIResponse[PaymentCreateResponse]:
    """Tạo giao dịch thanh toán VNPay sandbox cho 1 đơn hàng ĐÃ TỒN TẠI (đơn
    tạo trước qua `POST /orders`, luôn theo luồng COD-style hiện có - VNPay
    là lựa chọn thanh toán online BỔ SUNG, KHÔNG thay đổi cách tạo đơn). Trả
    về URL redirect sang trang thanh toán VNPay. Yêu cầu: Customer, đúng chủ
    đơn (`order.user_id == current_user.id`).
    """
    # request.client có thể None (VD test client) - IP giả hợp lệ để VNPay
    # không từ chối tham số vnp_IpAddr rỗng, KHÔNG dùng cho mục đích bảo mật
    # nào khác (không phía sau reverse proxy thật ở quy mô đồ án hiện tại).
    client_ip = request.client.host if request.client else "127.0.0.1"
    try:
        payment, payment_url = payment_service.create_payment_for_order(
            db, order_id=payload.order_id, user_id=current_user.id, client_ip=client_ip
        )
    except payment_service.PaymentNotFoundError:
        raise _not_found()
    except payment_service.PaymentForbiddenError:
        raise _forbidden_not_owner()
    except payment_service.PaymentConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except payment_service.PaymentGatewayNotConfiguredError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except payment_service.PaymentError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return success_response(
        data=PaymentCreateResponse(payment_id=payment.id, order_id=payment.order_id, payment_url=payment_url),
        message="Đã tạo giao dịch thanh toán",
    )


@router.get(
    "/callback",
    summary="Nhận kết quả thanh toán từ VNPay (vnp_ReturnUrl)",
)
def payment_callback(request: Request, db: Annotated[Session, Depends(get_db)]) -> RedirectResponse:
    """Public - xác thực bằng chữ ký (`vnp_SecureHash`) của VNPay, KHÔNG dùng
    JWT (VNPay/trình duyệt khách gọi tới đây, không mang theo token đăng nhập
    nào). Đây là target CỦA `vnp_ReturnUrl` (trình duyệt khách tự điều hướng
    tới sau khi thanh toán xong trên VNPay) - endpoint DUY NHẤT trong
    `docs/API_SPEC.md` mục 6 dùng cho cả xác minh callback LẪN đưa khách quay
    lại Frontend, nên response ở đây là REDIRECT (303) sang trang kết quả
    Frontend (`/checkout/payment-result`), KHÔNG PHẢI JSON - khách cần thấy
    giao diện thật, không phải response API trần.

    Không throw lỗi HTTP nào cho VNPay dù xác minh thất bại (chữ ký sai/không
    tìm thấy giao dịch/số tiền lệch) - luôn redirect về Frontend với trạng
    thái phù hợp (`status=invalid` nếu không xác minh được), xem docstring
    `payment_service.process_callback()`.
    """
    settings = get_settings()
    params = dict(request.query_params)
    payment, ok = payment_service.process_callback(db, params)

    frontend_base = settings.FRONTEND_BASE_URL.rstrip("/")
    if not ok or payment is None:
        return RedirectResponse(
            f"{frontend_base}/checkout/payment-result?status=invalid", status_code=status.HTTP_303_SEE_OTHER
        )

    result_status = "success" if payment.status.value == "success" else "failed"
    return RedirectResponse(
        f"{frontend_base}/checkout/payment-result?order_id={payment.order_id}&status={result_status}",
        status_code=status.HTTP_303_SEE_OTHER,
    )


@router.get(
    "/{order_id}/status",
    response_model=APIResponse[PaymentStatusRead],
    summary="Kiểm tra trạng thái thanh toán của 1 đơn hàng",
    responses=auth_responses(not_found=True),
)
def get_payment_status(
    order_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> APIResponse[PaymentStatusRead]:
    """Kiểm tra trạng thái thanh toán của 1 đơn hàng - 404 nếu đơn KHÔNG có
    giao dịch VNPay nào (VD đơn COD, hoặc đơn VNPay chưa từng bấm thanh
    toán). Yêu cầu: Customer (chủ đơn), Admin.

    Không dùng `require_role()` (cùng lý do `GET /orders/{id}`, xem
    `app/routers/order.py:get_order()`) - Customer CHỈ xem được đơn CỦA
    CHÍNH HỌ, Admin luôn xem được mọi đơn.
    """
    try:
        payment = payment_service.get_payment_status(
            db, order_id=order_id, user_id=current_user.id, is_admin=current_user.role == UserRole.admin
        )
    except payment_service.PaymentNotFoundError as e:
        # KHÔNG dùng `_not_found()` (message cố định "Không tìm thấy đơn
        # hàng") - service phân biệt 2 tình huống khác nhau ("đơn không tồn
        # tại" vs "đơn có thật nhưng chưa có giao dịch thanh toán online nào"),
        # giữ nguyên message CỤ THỂ đó cho Frontend hiển thị đúng.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except payment_service.PaymentForbiddenError:
        raise _forbidden_not_owner()

    return success_response(data=PaymentStatusRead.model_validate(payment))
