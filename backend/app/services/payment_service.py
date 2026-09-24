"""Business logic: Payment - VNPay sandbox THẬT (task "Quyết định và hoàn
thiện thanh toán", thay 3 endpoint `501` cũ task 8.1).

## Quyết định kiến trúc: Payment tạo SAU Order, KHÔNG đổi `checkout()`

`POST /orders` (`order_service.checkout()`) giữ NGUYÊN - luôn tạo `Order`
ngay lập tức (trừ tồn kho ngay), không có khái niệm "giữ chỗ chờ thanh
toán". Chọn thanh toán VNPay là bước THỨ HAI, xảy ra SAU khi `Order` đã tồn
tại (`POST /payments/create` nhận `order_id` - đúng khớp quan hệ 1-1
`payments.order_id` đã thiết kế sẵn trong DBML/model từ trước, xem
docs/DATABASE_SCHEMA.md). Lý do: `checkout()` là luồng transaction đã ổn
định/test kỹ (`SELECT ... FOR UPDATE`, khóa theo thứ tự tránh deadlock) -
dựng lại thành "giữ chỗ trước, có thanh toán mới tạo đơn thật" là thay đổi
kiến trúc LỚN, rủi ro cao, không tương xứng phạm vi "hoàn thiện thanh toán"
(không phải "redesign checkout"). Hệ quả chấp nhận: đơn "pending" vẫn giữ
tồn kho đã trừ dù Customer bỏ dở thanh toán VNPay - giống hệt rủi ro COD sẵn
có (khách đặt COD rồi không nhận hàng), Admin xử lý bằng quy trình hủy đơn
có sẵn (`PUT /orders/{id}/cancel`, tự hoàn kho), không cần cơ chế mới.

## KHÔNG gate `PUT /orders/{id}/status` theo `Payment.status`

Admin vẫn tự do đổi `pending -> confirmed` dù VNPay CHƯA `success` - quyết
định CÓ CHỦ ĐÍCH: kiểm tra đã thanh toán hay chưa trước khi xác nhận/giao
hàng là trách nhiệm NGHIỆP VỤ của Admin (xem trạng thái thanh toán hiện ở
chi tiết đơn qua `GET /payments/{order_id}/status`), không tự động khóa
cứng `order_service.VALID_STATUS_TRANSITIONS` đã test kỹ - ngoài phạm vi
task này.

## `vnp_TxnRef` = `Payment.id` (không sinh mã riêng)

`payments.id` (auto-increment, duy nhất TOÀN HỆ THỐNG - dư thừa so với yêu
cầu "duy nhất trong ngày" của VNPay) dùng LUÔN làm `vnp_TxnRef`, không cần
sinh/lưu thêm cột nào. Callback tra ngược `Payment` bằng chính giá trị này.

## Chỉ cho retry khi Payment đang "pending" hoặc "failed"

`payments.order_id` UNIQUE (quan hệ 1-1 THẬT theo DBML, không phải giới hạn
tự đặt thêm) - 1 Order chỉ có ĐÚNG 1 dòng Payment. "Thử lại" (Customer bấm
thanh toán VNPay lần nữa sau khi lần trước thất bại/bỏ dở) dùng LẠI CHÍNH
dòng đó (reset "failed" -> "pending", tạo URL VNPay MỚI với CÙNG
`vnp_TxnRef`) - không tạo dòng mới (vi phạm UNIQUE). "pending" (chưa có kết
quả) cũng cho tạo lại URL mới (VD link VNPay cũ hết hạn ~15 phút, hoặc user
đóng tab giữa chừng). "success"/"refunded" (đã xong) -> `PaymentConflictError`
(409), không cho thanh toán lại.

## Callback: CHỈ tin dữ liệu ĐÃ QUA XÁC MINH CHỮ KÝ, đối chiếu `Payment.amount` lưu SẴN

`vnp_SecureHash` PHẢI khớp lại đúng HMAC-SHA512(hash_secret, tham số còn lại
sắp xếp alphabet) - sai chữ ký -> từ chối THẲNG, KHÔNG đọc tiếp bất kỳ field
nào khác (có thể là request giả mạo hoàn toàn, không chỉ "status không đáng
tin"). Sau khi chữ ký ĐÚNG, `vnp_Amount` (chia 100, quy ước VNPay - đơn vị
nhỏ nhất, VND không có phần thập phân) PHẢI khớp CHÍNH XÁC `payment.amount`
đã lưu SẴN từ lúc `build_payment_url()` (KHÔNG tin số tiền callback tự khai)
- lệch số tiền (dù chữ ký hợp lệ - lý thuyết không nên xảy ra nhưng vẫn
phòng thủ) -> từ chối, KHÔNG cập nhật status.

## Idempotent - callback gọi lại nhiều lần cho CÙNG giao dịch KHÔNG xử lý lại

`with_for_update()` khi tra `Payment` (chống 2 callback gần như đồng thời
cùng đọc thấy "pending" rồi cùng xử lý) + CHỈ chuyển status khi đang
"pending" (`payment.status != PaymentStatus.pending` -> trả về nguyên
trạng, không lỗi, không cập nhật lại `transaction_id`/`updated_at` lần 2) -
callback thật của VNPay có thể gọi lại (mạng lag, retry tự động phía VNPay)
cho CÙNG 1 giao dịch.
"""

import hashlib
import hmac
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.order import Order, OrderStatus, Payment, PaymentStatus

# Response code VNPay coi là giao dịch THÀNH CÔNG - cả 2 field PHẢI cùng "00"
# (vnp_ResponseCode: kết quả gọi API; vnp_TransactionStatus: kết quả giao
# dịch thật - 2 khái niệm khác nhau theo tài liệu VNPay, chỉ "00" cả 2 mới
# tính là thanh toán thành công thật).
_VNPAY_SUCCESS_CODE = "00"


class PaymentError(Exception):
    """Lỗi nghiệp vụ chung (VD đơn đã hủy) - router dịch 400."""


class PaymentNotFoundError(Exception):
    """Không tìm thấy Order hoặc Payment liên quan - router dịch 404."""


class PaymentForbiddenError(Exception):
    """Order không thuộc về user đang gọi (không phải Admin) - router dịch 403."""


class PaymentConflictError(Exception):
    """Payment đã ở trạng thái cuối (success/refunded) - router dịch 409."""


class PaymentGatewayNotConfiguredError(Exception):
    """Thiếu VNPAY_TMN_CODE/VNPAY_HASH_SECRET - router dịch 503 (lỗi vận
    hành/cấu hình, không phải lỗi do Customer gây ra)."""


def _sign(params: dict[str, str], hash_secret: str) -> str:
    """HMAC-SHA512 theo ĐÚNG quy tắc VNPay: sort key alphabet, encode value
    kiểu `application/x-www-form-urlencoded` (`quote_plus` - dấu cách thành
    "+", KHÔNG PHẢI "%20"), nối "key=value" bằng "&". Dùng CHUNG hàm này cho
    CẢ ký lúc tạo URL LẪN xác minh lúc nhận callback - đảm bảo 2 chiều luôn
    nhất quán 1 thuật toán duy nhất."""
    query = "&".join(f"{key}={quote_plus(str(value))}" for key, value in sorted(params.items()))
    return hmac.new(hash_secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha512).hexdigest()


def build_payment_url(db: Session, order: Order, client_ip: str) -> tuple[Payment, str]:
    """Tạo (hoặc tái sử dụng) `Payment` cho `order`, trả về URL redirect sang
    VNPay. `order` đã được router validate tồn tại + đúng chủ - xem docstring
    module cho quy tắc tạo mới/reset "failed"/từ chối "success"/"refunded"."""
    settings = get_settings()
    if not settings.VNPAY_TMN_CODE or not settings.VNPAY_HASH_SECRET:
        raise PaymentGatewayNotConfiguredError(
            "Cổng thanh toán VNPay chưa được cấu hình (thiếu VNPAY_TMN_CODE/VNPAY_HASH_SECRET)"
        )
    if order.status == OrderStatus.cancelled:
        raise PaymentError("Đơn hàng đã bị hủy - không thể thanh toán")

    payment = db.query(Payment).filter(Payment.order_id == order.id).one_or_none()
    if payment is None:
        payment = Payment(
            order_id=order.id,
            payment_method="vnpay",
            amount=order.total_amount,
            status=PaymentStatus.pending,
        )
        db.add(payment)
        db.flush()  # payment.id có giá trị để dùng làm vnp_TxnRef, CHƯA commit
    elif payment.status == PaymentStatus.pending:
        pass  # cho tạo lại URL mới (link VNPay cũ có thể đã hết hạn) - giữ nguyên record
    elif payment.status == PaymentStatus.failed:
        payment.status = PaymentStatus.pending  # cho thử lại
    else:
        raise PaymentConflictError(
            f'Đơn hàng đã ở trạng thái thanh toán "{payment.status.value}" - không thể tạo giao dịch mới'
        )

    params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": settings.VNPAY_TMN_CODE,
        # VNPay dùng đơn vị nhỏ nhất (x100) - KHÔNG có phần thập phân cho VND.
        "vnp_Amount": str(int(payment.amount * 100)),
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": str(payment.id),
        "vnp_OrderInfo": f"Thanh toan don hang {order.id}",
        "vnp_OrderType": "other",
        "vnp_Locale": "vn",
        "vnp_ReturnUrl": settings.VNPAY_RETURN_URL,
        "vnp_IpAddr": client_ip,
        "vnp_CreateDate": datetime.now().strftime("%Y%m%d%H%M%S"),
    }
    secure_hash = _sign(params, settings.VNPAY_HASH_SECRET)
    query = "&".join(f"{key}={quote_plus(str(value))}" for key, value in sorted(params.items()))
    payment_url = f"{settings.VNPAY_PAY_URL}?{query}&vnp_SecureHash={secure_hash}"

    db.commit()
    db.refresh(payment)
    return payment, payment_url


def create_payment_for_order(db: Session, *, order_id: int, user_id: int, client_ip: str) -> tuple[Payment, str]:
    """Router gọi hàm này cho `POST /payments/create` (Customer) - validate
    Order tồn tại + đúng chủ TRƯỚC khi giao cho `build_payment_url()`."""
    order = db.get(Order, order_id)
    if order is None:
        raise PaymentNotFoundError("Không tìm thấy đơn hàng")
    if order.user_id != user_id:
        raise PaymentForbiddenError("Không có quyền thanh toán đơn hàng này")
    return build_payment_url(db, order, client_ip)


def process_callback(db: Session, params: dict[str, str]) -> tuple[Payment | None, bool]:
    """Xử lý `GET /payments/callback` (VNPay `vnp_ReturnUrl`) - xem docstring
    module cho quy tắc xác minh chữ ký/đối chiếu số tiền/idempotent.

    Trả về `(payment, ok)`: `ok=False` nghĩa là chữ ký sai/không tìm thấy
    Payment/số tiền lệch - router redirect Frontend về trang kết quả với
    trạng thái chung chung "invalid", KHÔNG có `order_id` cụ thể (không đủ
    tin cậy để tiết lộ đơn hàng nào bị ảnh hưởng nếu request có dấu hiệu giả
    mạo/hỏng)."""
    settings = get_settings()
    received_hash = params.get("vnp_SecureHash", "")
    signed_params = {k: v for k, v in params.items() if k not in ("vnp_SecureHash", "vnp_SecureHashType")}
    expected_hash = _sign(signed_params, settings.VNPAY_HASH_SECRET)
    if not received_hash or not hmac.compare_digest(received_hash.lower(), expected_hash.lower()):
        return None, False

    try:
        payment_id = int(params.get("vnp_TxnRef", ""))
    except ValueError:
        return None, False

    payment = db.query(Payment).filter(Payment.id == payment_id).with_for_update().one_or_none()
    if payment is None:
        db.rollback()
        return None, False

    try:
        callback_amount = Decimal(params.get("vnp_Amount", "0")) / 100
    except InvalidOperation:
        db.rollback()
        return payment, False
    if callback_amount != payment.amount:
        db.rollback()
        return payment, False

    if payment.status != PaymentStatus.pending:
        db.rollback()  # đã xử lý từ lần callback trước - KHÔNG cập nhật lại
        return payment, True

    response_code = params.get("vnp_ResponseCode", "")
    transaction_status = params.get("vnp_TransactionStatus", "")
    payment.transaction_id = params.get("vnp_TransactionNo") or None
    payment.status = (
        PaymentStatus.success
        if response_code == _VNPAY_SUCCESS_CODE and transaction_status == _VNPAY_SUCCESS_CODE
        else PaymentStatus.failed
    )
    db.commit()
    db.refresh(payment)
    return payment, True


def get_payment_status(db: Session, *, order_id: int, user_id: int, is_admin: bool) -> Payment:
    """Router gọi hàm này cho `GET /payments/{order_id}/status` (Customer
    chủ đơn, hoặc Admin)."""
    order = db.get(Order, order_id)
    if order is None:
        raise PaymentNotFoundError("Không tìm thấy đơn hàng")
    if not is_admin and order.user_id != user_id:
        raise PaymentForbiddenError("Không có quyền xem đơn hàng này")

    payment = db.query(Payment).filter(Payment.order_id == order_id).one_or_none()
    if payment is None:
        raise PaymentNotFoundError("Đơn hàng này chưa có giao dịch thanh toán online (COD hoặc chưa khởi tạo)")
    return payment
