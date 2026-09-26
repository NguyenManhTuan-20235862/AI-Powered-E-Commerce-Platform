"""Test API Payment - VNPay sandbox THẬT (task "Quyết định và hoàn thiện
thanh toán") - end-to-end qua HTTP thật, MySQL thật, cùng convention
`test_order.py`.

Dùng LẠI `_sign()` của chính `payment_service` (white-box, KHÔNG tự dựng lại
thuật toán HMAC riêng cho test - nếu 2 nơi lệch nhau, test sẽ tự vô nghĩa vì
luôn "tự ký rồi tự verify đúng bằng chính công thức đang test") để build
tham số callback GIẢ LẬP THẬT ĐÚNG những gì VNPay gửi về - test round-trip
"tạo giao dịch -> nhận callback" đầy đủ, không mock từng bước.
"""

import threading
from datetime import datetime
from decimal import Decimal
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.order import Order, OrderStatus, Payment, PaymentStatus
from app.models.product import Product
from app.services.payment_service import _sign
from tests.test_order import VALID_CHECKOUT_PAYLOAD, _add_to_cart, _admin_headers, _create_category, _create_product, _customer_headers

VNPAY_TMN_CODE = "TESTCODE01"
VNPAY_HASH_SECRET = "TESTSECRETKEY0123456789"


@pytest.fixture(autouse=True)
def _vnpay_configured(monkeypatch):
    """Mặc định "đã cấu hình" VNPay cho MỌI test trong file này - test riêng
    case "chưa cấu hình" (503) tự set rỗng lại bên trong test đó."""
    settings = get_settings()
    monkeypatch.setattr(settings, "VNPAY_TMN_CODE", VNPAY_TMN_CODE)
    monkeypatch.setattr(settings, "VNPAY_HASH_SECRET", VNPAY_HASH_SECRET)
    monkeypatch.setattr(settings, "VNPAY_RETURN_URL", "http://localhost:8000/api/v1/payments/callback")
    monkeypatch.setattr(settings, "FRONTEND_BASE_URL", "http://localhost:3000")


def _create_order(client: TestClient, db: Session, headers: dict, *, price: str = "100000") -> dict:
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=10, price=price)
    _add_to_cart(client, headers, product.id, quantity=1)
    response = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _extract_payment_url_params(payment_url: str) -> dict[str, str]:
    query = urlparse(payment_url).query
    return {k: v[0] for k, v in parse_qs(query).items()}


def _valid_callback_params(payment_url_params: dict[str, str], *, response_code: str = "00") -> dict[str, str]:
    """Dựng bộ tham số callback GIỐNG HỆT VNPay sẽ gửi cho 1 giao dịch THÀNH
    CÔNG/THẤT BẠI - lấy lại `vnp_TxnRef`/`vnp_Amount` ĐÚNG từ URL đã tạo
    (không phải tự bịa) rồi tự ký lại bằng `_sign()` (mô phỏng phía VNPay)."""
    params = {
        "vnp_Amount": payment_url_params["vnp_Amount"],
        "vnp_BankCode": "NCB",
        "vnp_OrderInfo": payment_url_params["vnp_OrderInfo"],
        "vnp_PayDate": datetime.now().strftime("%Y%m%d%H%M%S"),
        "vnp_ResponseCode": response_code,
        "vnp_TmnCode": VNPAY_TMN_CODE,
        "vnp_TransactionNo": "14000123",
        "vnp_TransactionStatus": response_code,
        "vnp_TxnRef": payment_url_params["vnp_TxnRef"],
    }
    params["vnp_SecureHash"] = _sign(params, VNPAY_HASH_SECRET)
    return params


# ---- POST /payments/create ----


def test_create_payment_requires_customer_role(client: TestClient, db: Session) -> None:
    order = _create_order(client, db, _customer_headers(db))
    response = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=_admin_headers(db))
    assert response.status_code == 403


def test_create_payment_without_auth_returns_401(client: TestClient) -> None:
    response = client.post("/api/v1/payments/create", json={"order_id": 1})
    assert response.status_code == 401


def test_create_payment_order_not_found_returns_404(client: TestClient, db: Session) -> None:
    response = client.post("/api/v1/payments/create", json={"order_id": 999999}, headers=_customer_headers(db))
    assert response.status_code == 404


def test_create_payment_other_customer_order_returns_403(client: TestClient, db: Session) -> None:
    owner_headers = _customer_headers(db)
    order = _create_order(client, db, owner_headers)
    other_headers = _customer_headers(db)
    response = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=other_headers)
    assert response.status_code == 403


def test_create_payment_not_configured_returns_503(client: TestClient, db: Session, monkeypatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "VNPAY_TMN_CODE", "")
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    response = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    assert response.status_code == 503


def test_create_payment_success_returns_signed_url_and_creates_payment_row(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    order = _create_order(client, db, headers, price="150000")

    response = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["order_id"] == order["id"]
    assert data["payment_url"].startswith("https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?")

    params = _extract_payment_url_params(data["payment_url"])
    # vnp_TxnRef = "{payment_id}A{attempt}" - lần đầu là attempt 1 (task "Chốt
    # các trường hợp lỗi và retry" - mỗi lần thử có ref riêng, xem payment_service.py).
    assert params["vnp_TxnRef"] == f"{data['payment_id']}A1"
    assert params["vnp_Amount"] == "15000000"  # 150000 * 100
    assert params["vnp_TmnCode"] == VNPAY_TMN_CODE
    assert "vnp_SecureHash" in params

    db.commit()
    payment = db.get(Payment, data["payment_id"])
    assert payment.order_id == order["id"]
    assert payment.payment_method == "vnpay"
    assert payment.status == PaymentStatus.pending
    assert payment.amount == Decimal("150000.00")


def test_create_payment_cancelled_order_returns_400(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    cancel = client.put(f"/api/v1/orders/{order['id']}/cancel", headers=headers)
    assert cancel.status_code == 200, cancel.text

    response = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    assert response.status_code == 400


def test_create_payment_already_success_returns_409(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    first = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    params = _extract_payment_url_params(first.json()["data"]["payment_url"])
    client.get("/api/v1/payments/callback", params=_valid_callback_params(params, response_code="00"))

    response = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    assert response.status_code == 409


def test_create_payment_retry_after_failed_resets_to_pending_same_payment_row(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    first = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    first_payment_id = first.json()["data"]["payment_id"]
    params = _extract_payment_url_params(first.json()["data"]["payment_url"])
    client.get("/api/v1/payments/callback", params=_valid_callback_params(params, response_code="24"))  # khách hủy giao dịch
    db.commit()
    assert db.get(Payment, first_payment_id).status == PaymentStatus.failed

    first_txn_ref = _extract_payment_url_params(first.json()["data"]["payment_url"])["vnp_TxnRef"]

    retry = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    assert retry.status_code == 201, retry.text
    assert retry.json()["data"]["payment_id"] == first_payment_id  # DÙNG LẠI đúng 1 dòng (order_id UNIQUE)
    # Lần thử MỚI có vnp_TxnRef KHÁC lần cũ (attempt tăng) - để callback lần cũ
    # không tác động sang lần mới (xem test_late_callback_* bên dưới).
    retry_txn_ref = _extract_payment_url_params(retry.json()["data"]["payment_url"])["vnp_TxnRef"]
    assert retry_txn_ref != first_txn_ref
    db.commit()
    assert db.get(Payment, first_payment_id).status == PaymentStatus.pending
    assert db.get(Payment, first_payment_id).txn_ref == retry_txn_ref  # bản mới nhất


# ---- GET /payments/callback ----


def test_callback_valid_success_redirects_and_updates_status(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    created = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    payment_id = created.json()["data"]["payment_id"]
    params = _extract_payment_url_params(created.json()["data"]["payment_url"])

    response = client.get(
        "/api/v1/payments/callback", params=_valid_callback_params(params, response_code="00"), follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == f"http://localhost:3000/checkout/payment-result?order_id={order['id']}&status=success"

    db.commit()
    payment = db.get(Payment, payment_id)
    assert payment.status == PaymentStatus.success
    assert payment.transaction_id == "14000123"


def test_callback_valid_failure_code_marks_failed(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    created = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    payment_id = created.json()["data"]["payment_id"]
    params = _extract_payment_url_params(created.json()["data"]["payment_url"])

    response = client.get(
        "/api/v1/payments/callback", params=_valid_callback_params(params, response_code="24"), follow_redirects=False
    )
    assert response.status_code == 303
    assert f"order_id={order['id']}&status=failed" in response.headers["location"]

    db.commit()
    assert db.get(Payment, payment_id).status == PaymentStatus.failed


def test_callback_invalid_signature_redirects_invalid_and_does_not_update(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    created = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    payment_id = created.json()["data"]["payment_id"]
    params = _extract_payment_url_params(created.json()["data"]["payment_url"])

    callback_params = _valid_callback_params(params, response_code="00")
    callback_params["vnp_SecureHash"] = "0" * 128  # chữ ký giả mạo

    response = client.get("/api/v1/payments/callback", params=callback_params, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:3000/checkout/payment-result?status=invalid"

    db.commit()
    assert db.get(Payment, payment_id).status == PaymentStatus.pending  # KHÔNG đổi


def test_callback_amount_mismatch_redirects_invalid_and_does_not_update(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    created = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    payment_id = created.json()["data"]["payment_id"]
    params = _extract_payment_url_params(created.json()["data"]["payment_url"])

    tampered_params = dict(params)
    tampered_params["vnp_Amount"] = str(int(params["vnp_Amount"]) * 2)  # số tiền bị đổi
    callback_params = _valid_callback_params(tampered_params, response_code="00")

    response = client.get("/api/v1/payments/callback", params=callback_params, follow_redirects=False)
    assert response.status_code == 303
    assert "status=invalid" in response.headers["location"]

    db.commit()
    assert db.get(Payment, payment_id).status == PaymentStatus.pending


def test_callback_is_idempotent_second_delivery_does_not_reprocess(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    created = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    payment_id = created.json()["data"]["payment_id"]
    params = _extract_payment_url_params(created.json()["data"]["payment_url"])

    first_callback = _valid_callback_params(params, response_code="00")
    client.get("/api/v1/payments/callback", params=first_callback, follow_redirects=False)
    db.commit()
    assert db.get(Payment, payment_id).transaction_id == "14000123"

    # VNPay gọi lại (mạng lag/retry) CHO CÙNG giao dịch - lần này khác
    # `vnp_TransactionNo` để CHỨNG MINH lần 2 KHÔNG được xử lý lại (nếu bị xử
    # lý lại, transaction_id sẽ đổi thành giá trị này).
    second_params = _valid_callback_params(params, response_code="00")
    second_params["vnp_TransactionNo"] = "99999999"
    second_params["vnp_SecureHash"] = _sign(
        {k: v for k, v in second_params.items() if k != "vnp_SecureHash"}, VNPAY_HASH_SECRET
    )
    response = client.get("/api/v1/payments/callback", params=second_params, follow_redirects=False)
    assert response.status_code == 303
    assert f"order_id={order['id']}&status=success" in response.headers["location"]

    db.commit()
    payment = db.get(Payment, payment_id)
    assert payment.status == PaymentStatus.success
    assert payment.transaction_id == "14000123"  # VẪN giá trị của lần ĐẦU, không bị ghi đè


def test_callback_unknown_txn_ref_redirects_invalid(client: TestClient) -> None:
    response = client.get(
        "/api/v1/payments/callback",
        params={"vnp_TxnRef": "999999999", "vnp_Amount": "10000", "vnp_ResponseCode": "00", "vnp_SecureHash": "invalid"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"] == "http://localhost:3000/checkout/payment-result?status=invalid"


# ---- Hardening (task "Chốt các trường hợp lỗi và retry của thanh toán") ----


def test_late_callback_from_superseded_attempt_is_rejected(client: TestClient, db: Session) -> None:
    """Callback của LẦN THỬ CŨ (đến trễ) SAU khi khách đã bấm thử lại (lần thử
    mới) KHÔNG được tác động vào Payment - `vnp_TxnRef` lần cũ không còn khớp
    dòng nào (đã bị đổi sang ref lần mới) -> bị từ chối stale. Chỉ lần thử MỚI
    NHẤT được tin (#2)."""
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)

    first = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    payment_id = first.json()["data"]["payment_id"]
    first_params = _extract_payment_url_params(first.json()["data"]["payment_url"])  # attempt 1 (txn "..A1")

    # Khách bấm "thử lại" -> lần thử MỚI (attempt 2, txn "..A2") trước khi lần
    # cũ có kết quả.
    second = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    second_params = _extract_payment_url_params(second.json()["data"]["payment_url"])
    assert first_params["vnp_TxnRef"] != second_params["vnp_TxnRef"]

    # Callback THÀNH CÔNG của LẦN CŨ (attempt 1) đến trễ -> phải bị từ chối,
    # KHÔNG đổi trạng thái payment.
    late = client.get(
        "/api/v1/payments/callback", params=_valid_callback_params(first_params, response_code="00"), follow_redirects=False
    )
    assert late.status_code == 303
    assert late.headers["location"] == "http://localhost:3000/checkout/payment-result?status=invalid"
    db.commit()
    assert db.get(Payment, payment_id).status == PaymentStatus.pending  # KHÔNG bị lần cũ set success

    # Callback của LẦN MỚI NHẤT (attempt 2) vẫn xử lý bình thường.
    ok = client.get(
        "/api/v1/payments/callback", params=_valid_callback_params(second_params, response_code="00"), follow_redirects=False
    )
    assert ok.status_code == 303
    assert f"order_id={order['id']}&status=success" in ok.headers["location"]
    db.commit()
    assert db.get(Payment, payment_id).status == PaymentStatus.success


def test_concurrent_create_reuses_single_payment_row_no_error(client: TestClient, db: Session) -> None:
    """2 request tạo giao dịch ĐỒNG THỜI (thread thật + barrier) cho CÙNG 1 đơn
    - CẢ 2 thành công (201, không 500 do đụng UNIQUE(order_id)), chỉ tạo ĐÚNG 1
    dòng Payment, attempt_count = 2 (mỗi request 1 lần thử). Khóa Order
    serialize 2 request (#3)."""
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)

    barrier = threading.Barrier(2)
    results: dict[str, int] = {}

    def create(name: str) -> None:
        barrier.wait()
        response = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
        results[name] = response.status_code

    t_a = threading.Thread(target=create, args=("a",))
    t_b = threading.Thread(target=create, args=("b",))
    t_a.start()
    t_b.start()
    t_a.join()
    t_b.join()

    assert sorted(results.values()) == [201, 201]

    db.commit()
    payments = db.query(Payment).filter(Payment.order_id == order["id"]).all()
    assert len(payments) == 1  # đúng 1 dòng - KHÔNG tạo trùng
    assert payments[0].attempt_count == 2  # mỗi request đóng góp 1 lần thử


def test_callback_success_on_cancelled_order_records_payment_without_double_restock(
    client: TestClient, db: Session
) -> None:
    """Callback THÀNH CÔNG đến SAU khi đơn đã hủy (#4a): ghi nhận trung thực
    (success + transaction_id, KHÔNG mất dấu tiền) nhưng KHÔNG hoàn kho lần 2
    (kho đã hoàn lúc hủy) và KHÔNG "hồi sinh" đơn (vẫn cancelled)."""
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    product_id = order["items"][0]["product_id"]

    created = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    payment_id = created.json()["data"]["payment_id"]
    params = _extract_payment_url_params(created.json()["data"]["payment_url"])

    # Hủy đơn (payment còn pending -> hủy được, hoàn kho). Chụp tồn kho sau hủy.
    assert client.put(f"/api/v1/orders/{order['id']}/cancel", headers=headers).status_code == 200
    db.commit()
    stock_after_cancel = db.get(Product, product_id).stock_quantity

    # Callback thành công đến trễ.
    response = client.get(
        "/api/v1/payments/callback", params=_valid_callback_params(params, response_code="00"), follow_redirects=False
    )
    assert response.status_code == 303
    db.commit()

    payment = db.get(Payment, payment_id)
    assert payment.status == PaymentStatus.success  # ghi nhận trung thực tiền đã thu
    assert payment.transaction_id == "14000123"
    assert db.get(Order, order["id"]).status == OrderStatus.cancelled  # KHÔNG hồi sinh đơn
    assert db.get(Product, product_id).stock_quantity == stock_after_cancel  # KHÔNG hoàn kho lần 2


def test_customer_cannot_cancel_paid_order_returns_409(client: TestClient, db: Session) -> None:
    """Customer KHÔNG tự hủy được đơn đã thanh toán online thành công (#4b) -
    409, đơn giữ nguyên (không hoàn kho), tiền không bị "mất dấu"."""
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    product_id = order["items"][0]["product_id"]

    created = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    params = _extract_payment_url_params(created.json()["data"]["payment_url"])
    client.get("/api/v1/payments/callback", params=_valid_callback_params(params, response_code="00"))
    db.commit()
    stock_after_paid = db.get(Product, product_id).stock_quantity

    cancel = client.put(f"/api/v1/orders/{order['id']}/cancel", headers=headers)
    assert cancel.status_code == 409

    db.commit()
    assert db.get(Order, order["id"]).status == OrderStatus.pending  # KHÔNG bị hủy
    assert db.get(Product, product_id).stock_quantity == stock_after_paid  # KHÔNG hoàn kho


def test_admin_can_cancel_paid_order(client: TestClient, db: Session) -> None:
    """Admin VẪN hủy được đơn đã thanh toán (khác Customer) - có thẩm quyền,
    tự xử lý hoàn tiền thủ công (#4b)."""
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)

    created = client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)
    params = _extract_payment_url_params(created.json()["data"]["payment_url"])
    client.get("/api/v1/payments/callback", params=_valid_callback_params(params, response_code="00"))
    db.commit()

    response = client.put(
        f"/api/v1/orders/{order['id']}/status", json={"status": "cancelled"}, headers=_admin_headers(db)
    )
    assert response.status_code == 200, response.text
    db.commit()
    assert db.get(Order, order["id"]).status == OrderStatus.cancelled


# ---- GET /payments/{order_id}/status ----


def test_get_payment_status_no_payment_yet_returns_404(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    response = client.get(f"/api/v1/payments/{order['id']}/status", headers=headers)
    assert response.status_code == 404


def test_get_payment_status_owner_sees_own_payment(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)

    response = client.get(f"/api/v1/payments/{order['id']}/status", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["order_id"] == order["id"]
    assert data["payment_method"] == "vnpay"
    assert data["status"] == "pending"


def test_get_payment_status_admin_can_view_any(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    order = _create_order(client, db, headers)
    client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=headers)

    response = client.get(f"/api/v1/payments/{order['id']}/status", headers=_admin_headers(db))
    assert response.status_code == 200


def test_get_payment_status_other_customer_returns_403(client: TestClient, db: Session) -> None:
    owner_headers = _customer_headers(db)
    order = _create_order(client, db, owner_headers)
    client.post("/api/v1/payments/create", json={"order_id": order["id"]}, headers=owner_headers)

    other_headers = _customer_headers(db)
    response = client.get(f"/api/v1/payments/{order['id']}/status", headers=other_headers)
    assert response.status_code == 403
