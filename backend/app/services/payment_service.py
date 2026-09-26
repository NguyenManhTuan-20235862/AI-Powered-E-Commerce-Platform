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

## `vnp_TxnRef` = "{payment.id}A{attempt_count}" (DUY NHẤT theo TỪNG LẦN THỬ)

Trước đây `vnp_TxnRef = str(payment.id)` cố định - nhưng 1 dòng Payment được
retry nhiều lần (reset "failed"->"pending"), tất cả các lần đều dùng CÙNG
`vnp_TxnRef` -> callback của LẦN THỬ CŨ (đến trễ) có thể tác động sang lần thử
MỚI (cùng ref, cùng số tiền, chữ ký vẫn hợp lệ). Sửa (task "Chốt các trường
hợp lỗi và retry"): mỗi lần tạo URL tăng `attempt_count` và đặt `txn_ref =
"{id}A{attempt}"` (VD "5A1", "5A2"...). Callback tra ngược Payment theo CHÍNH
`txn_ref` HIỆN TẠI - callback mang ref của lần thử đã bị thay thế sẽ KHÔNG
khớp dòng nào -> bị từ chối là "stale". Chỉ lần thử MỚI NHẤT được tin. `txn_ref`
UNIQUE ở tầng DB (thêm cùng `attempt_count` qua migration b2c9d4e7f1a3). Cũng
đúng hơn với spec VNPay (yêu cầu `vnp_TxnRef` duy nhất theo từng giao dịch).

## Chỉ cho retry khi Payment đang "pending" hoặc "failed"

`payments.order_id` UNIQUE (quan hệ 1-1 THẬT theo DBML, không phải giới hạn
tự đặt thêm) - 1 Order chỉ có ĐÚNG 1 dòng Payment. "Thử lại" (Customer bấm
thanh toán VNPay lần nữa sau khi lần trước thất bại/bỏ dở) dùng LẠI CHÍNH
dòng đó (reset "failed" -> "pending", tạo URL VNPay MỚI với `vnp_TxnRef` MỚI
- xem trên) - không tạo dòng mới (vi phạm UNIQUE). "pending" (chưa có kết
quả) cũng cho tạo lại URL mới (VD link VNPay cũ hết hạn ~15 phút, hoặc user
đóng tab giữa chừng). "success"/"refunded" (đã xong) -> `PaymentConflictError`
(409), không cho thanh toán lại.

## Khóa Order khi tạo giao dịch (chống 2 request create/retry đồng thời)

`build_payment_url()` khóa Order (`SELECT ... FOR UPDATE`) TRƯỚC khi đọc/ghi
Payment (cùng kỷ luật khóa như `checkout()`/`cancel_order()`). 2 request
create/retry gần như đồng thời cho CÙNG 1 đơn sẽ serialize: request đầu tạo
dòng Payment rồi commit (nhả khóa), request sau mới đọc -> thấy dòng đã có ->
tái sử dụng (tăng attempt), KHÔNG đụng UNIQUE(order_id) gây 500. Đọc Payment
cũng dùng `with_for_update()` để thấy đúng bản mới nhất đã commit (locking read
đọc latest committed, không dính snapshot cũ của REPEATABLE READ).

## Callback trên đơn ĐÃ HỦY - ghi nhận trung thực, KHÔNG hoàn kho lần 2

Nếu callback THÀNH CÔNG đến SAU khi đơn đã bị hủy (kho đã hoàn lúc hủy):
`process_callback()` VẪN ghi nhận `status=success` + `transaction_id` (KHÔNG
mất dấu vết tiền VNPay đã thu), nhưng KHÔNG động vào đơn/không hoàn kho lần 2.
Tình huống "order cancelled + payment success" chính là CỜ CẦN HOÀN TIỀN thủ
công (auto-refund qua VNPay refund API ngoài phạm vi đồ án, xem
docs/KNOWN_TODOS.md) - ghi log cảnh báo để Admin dễ đối soát. Khóa theo thứ tự
Order -> Payment (CÙNG thứ tự `build_payment_url`) tránh deadlock giữa 1
callback và 1 retry đồng thời.

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
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.order import Order, OrderStatus, Payment, PaymentStatus

logger = logging.getLogger(__name__)

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

    # Khóa Order TRƯỚC (serialize 2 request create/retry đồng thời + đọc status
    # mới nhất) - xem docstring module. `with_for_update` cũng lấy đúng
    # `total_amount` mới nhất đã commit.
    db.refresh(order, with_for_update=True)
    if order.status == OrderStatus.cancelled:
        raise PaymentError("Đơn hàng đã bị hủy - không thể thanh toán")

    # `with_for_update()` - locking read thấy đúng dòng Payment mới nhất đã
    # commit (kể cả do request đồng thời vừa tạo), tránh dính snapshot cũ.
    payment = db.query(Payment).filter(Payment.order_id == order.id).with_for_update().one_or_none()
    if payment is None:
        payment = Payment(
            order_id=order.id,
            payment_method="vnpay",
            amount=order.total_amount,
            status=PaymentStatus.pending,
        )
        db.add(payment)
        db.flush()  # payment.id có giá trị để dựng txn_ref, CHƯA commit
    elif payment.status == PaymentStatus.pending:
        pass  # cho tạo lại URL mới (link VNPay cũ có thể đã hết hạn) - giữ nguyên record
    elif payment.status == PaymentStatus.failed:
        payment.status = PaymentStatus.pending  # cho thử lại
    else:
        raise PaymentConflictError(
            f'Đơn hàng đã ở trạng thái thanh toán "{payment.status.value}" - không thể tạo giao dịch mới'
        )

    # Mỗi lần tạo URL = 1 LẦN THỬ mới: tăng attempt + đổi txn_ref -> callback
    # của lần thử CŨ (txn_ref cũ) không còn khớp dòng nào -> bị từ chối stale.
    payment.attempt_count += 1
    payment.txn_ref = f"{payment.id}A{payment.attempt_count}"

    params = {
        "vnp_Version": "2.1.0",
        "vnp_Command": "pay",
        "vnp_TmnCode": settings.VNPAY_TMN_CODE,
        # VNPay dùng đơn vị nhỏ nhất (x100) - KHÔNG có phần thập phân cho VND.
        "vnp_Amount": str(int(payment.amount * 100)),
        "vnp_CurrCode": "VND",
        "vnp_TxnRef": payment.txn_ref,
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

    txn_ref = params.get("vnp_TxnRef", "")
    if not txn_ref:
        return None, False

    # Đọc KHÔNG khóa để lấy order_id (BẤT BIẾN 1 khi đã set) - rồi khóa Order
    # TRƯỚC, Payment SAU (CÙNG thứ tự order->payment như build_payment_url,
    # tránh deadlock giữa callback và retry đồng thời). Không tìm thấy txn_ref
    # = ref lạ HOẶC ref của lần thử đã bị retry thay thế -> từ chối stale.
    payment = db.query(Payment).filter(Payment.txn_ref == txn_ref).one_or_none()
    if payment is None:
        return None, False

    db.query(Order).filter(Order.id == payment.order_id).with_for_update().one()
    # Đọc lại Payment DƯỚI KHÓA (theo txn_ref) - nếu 1 retry chen vào giữa lúc
    # chờ khóa Order đã đổi txn_ref, lần đọc này trả None -> từ chối stale.
    payment = db.query(Payment).filter(Payment.txn_ref == txn_ref).with_for_update().one_or_none()
    if payment is None:
        db.rollback()
        return None, False
    order = db.get(Order, payment.order_id)

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
    is_success = response_code == _VNPAY_SUCCESS_CODE and transaction_status == _VNPAY_SUCCESS_CODE
    payment.transaction_id = params.get("vnp_TransactionNo") or None
    payment.status = PaymentStatus.success if is_success else PaymentStatus.failed

    # Callback THÀNH CÔNG trên đơn ĐÃ HỦY: ghi nhận trung thực (đã làm ở trên -
    # status=success + transaction_id, KHÔNG mất dấu tiền), KHÔNG hoàn kho lần 2
    # (kho đã hoàn lúc hủy). "cancelled + success" = cờ cần hoàn tiền thủ công.
    if is_success and order is not None and order.status == OrderStatus.cancelled:
        logger.warning(
            "VNPay callback THÀNH CÔNG cho đơn ĐÃ HỦY: order_id=%s payment_id=%s transaction_id=%s "
            "- tiền đã bị thu cho đơn không còn hiệu lực, CẦN HOÀN TIỀN thủ công",
            order.id,
            payment.id,
            payment.transaction_id,
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
