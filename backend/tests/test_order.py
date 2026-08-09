"""Test API Order (task 3.4.2) - end-to-end qua HTTP thật, MySQL thật.

Đây là nơi ĐẦU TIÊN trong dự án verify `SELECT ... FOR UPDATE` thật bằng
concurrency THẬT (threading, không chỉ gọi tuần tự 2 lần) - xem
`test_checkout_*_concurrent_*` bên dưới.
"""

import threading
from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.category import Category
from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.models.user import User, UserRole

VALID_CHECKOUT_PAYLOAD = {
    "shipping_name": "Nguyễn Văn A",
    "shipping_address": "123 Đường ABC, Q1, TP.HCM",
    "shipping_phone": "0900000000",
}


def _create_category(db: Session) -> Category:
    category = Category(name="Danh mục", slug=f"cat-{datetime.now().timestamp()}")
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _create_product(db: Session, category_id: int, *, stock_quantity: int = 10, price: str = "100000") -> Product:
    product = Product(
        category_id=category_id,
        name="Sản phẩm test",
        slug=f"sp-{datetime.now().timestamp()}-{stock_quantity}",
        price=Decimal(price),
        stock_quantity=stock_quantity,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _create_customer(db: Session) -> User:
    user = User(
        email=f"customer-{datetime.now().timestamp()}@example.com",
        password_hash=hash_password("password123"),
        full_name="Customer Test",
        role=UserRole.customer,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _headers_for(user: User) -> dict:
    token = create_access_token(user_id=user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _customer_headers(db: Session) -> dict:
    return _headers_for(_create_customer(db))


def _admin_headers(db: Session) -> dict:
    user = User(
        email=f"admin-{datetime.now().timestamp()}@example.com",
        password_hash=hash_password("password123"),
        full_name="Admin Test",
        role=UserRole.admin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _headers_for(user)


def _add_to_cart(client: TestClient, headers: dict, product_id: int, quantity: int = 1) -> None:
    response = client.post("/api/v1/cart/items", json={"product_id": product_id, "quantity": quantity}, headers=headers)
    assert response.status_code == 201, response.text


# ---- Checkout cơ bản ----


def test_checkout_empty_cart_returns_409(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    response = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers)
    assert response.status_code == 409


def test_checkout_success_decrements_stock_and_clears_cart(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=10, price="50000")
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id, quantity=3)

    response = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers)
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "pending"
    assert data["total_amount"] == "150000.00"
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 3
    assert data["items"][0]["price_at_purchase"] == "50000.00"
    assert data["items"][0]["product_name"] == product.name

    db.commit()  # đóng snapshot cũ trước khi đọc lại - xem test_product.py
    assert db.get(Product, product.id).stock_quantity == 7

    cart = client.get("/api/v1/cart", headers=headers)
    assert cart.json()["data"]["items"] == []


def test_checkout_insufficient_stock_returns_409_and_does_not_change_stock(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=2)
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id, quantity=2)

    # Admin âm thầm giảm tồn kho (mô phỏng thay đổi giữa lúc thêm giỏ và lúc
    # đặt hàng) - checkout PHẢI kiểm tra lại, không tin vào lúc thêm giỏ.
    product.stock_quantity = 1
    db.commit()

    response = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers)
    assert response.status_code == 409
    assert product.name in response.json()["message"]

    db.commit()
    assert db.get(Product, product.id).stock_quantity == 1  # không đổi - rollback đúng


def test_checkout_snapshots_product_name_and_price(client: TestClient, db: Session) -> None:
    """order_items snapshot tên/giá TẠI THỜI ĐIỂM mua - đổi giá/tên sản phẩm
    SAU KHI đặt hàng KHÔNG ảnh hưởng đơn đã tạo."""
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=10, price="80000")
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id, quantity=1)

    order_response = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers)
    order_id = order_response.json()["data"]["id"]

    product.name = "Tên đã đổi"
    product.price = Decimal("999999")
    db.commit()

    detail = client.get(f"/api/v1/orders/{order_id}", headers=headers)
    item = detail.json()["data"]["items"][0]
    assert item["product_name"] != "Tên đã đổi"
    assert item["price_at_purchase"] == "80000.00"


# ---- Concurrency thật: SELECT FOR UPDATE ----


def test_checkout_concurrent_only_one_succeeds_when_stock_insufficient(client: TestClient, db: Session) -> None:
    """2 user đặt hàng ĐỒNG THỜI (thread thật + barrier đồng bộ, KHÔNG gọi
    tuần tự) cùng 1 sản phẩm chỉ còn đủ hàng cho 1 đơn - CHỈ 1 đơn thành
    công (201), đơn kia nhận lỗi rõ ràng (409), tồn kho cuối KHÔNG âm.
    """
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=1)

    headers_a = _customer_headers(db)
    headers_b = _customer_headers(db)
    _add_to_cart(client, headers_a, product.id, quantity=1)
    _add_to_cart(client, headers_b, product.id, quantity=1)

    barrier = threading.Barrier(2)
    results: dict[str, int] = {}

    def checkout(name: str, headers: dict) -> None:
        barrier.wait()  # cả 2 thread cùng gọi POST /orders GẦN NHƯ ĐỒNG THỜI
        response = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers)
        results[name] = response.status_code

    t_a = threading.Thread(target=checkout, args=("a", headers_a))
    t_b = threading.Thread(target=checkout, args=("b", headers_b))
    t_a.start()
    t_b.start()
    t_a.join()
    t_b.join()

    assert sorted(results.values()) == [201, 409]

    db.commit()
    final_stock = db.get(Product, product.id).stock_quantity
    assert final_stock == 0  # ĐÚNG 1 đơn trừ kho - KHÔNG âm, KHÔNG trừ 2 lần


def test_checkout_concurrent_both_succeed_when_stock_sufficient(client: TestClient, db: Session) -> None:
    """Đối chứng: khóa (FOR UPDATE) KHÔNG chặn nhầm 2 giao dịch hợp lệ - đủ
    tồn kho cho CẢ 2 thì CẢ 2 đều phải thành công (không phải cứ concurrent
    là 1 thắng 1 thua)."""
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=2)

    headers_a = _customer_headers(db)
    headers_b = _customer_headers(db)
    _add_to_cart(client, headers_a, product.id, quantity=1)
    _add_to_cart(client, headers_b, product.id, quantity=1)

    barrier = threading.Barrier(2)
    results: dict[str, int] = {}

    def checkout(name: str, headers: dict) -> None:
        barrier.wait()
        response = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers)
        results[name] = response.status_code

    t_a = threading.Thread(target=checkout, args=("a", headers_a))
    t_b = threading.Thread(target=checkout, args=("b", headers_b))
    t_a.start()
    t_b.start()
    t_a.join()
    t_b.join()

    assert sorted(results.values()) == [201, 201]

    db.commit()
    assert db.get(Product, product.id).stock_quantity == 0


# ---- Ownership: GET /orders/{id}, PUT /orders/{id}/cancel ----


def test_get_order_owner_can_view(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers).json()["data"]["id"]

    response = client.get(f"/api/v1/orders/{order_id}", headers=headers)
    assert response.status_code == 200


def test_get_order_other_customer_gets_403(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    owner_headers = _customer_headers(db)
    _add_to_cart(client, owner_headers, product.id)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=owner_headers).json()["data"]["id"]

    other_headers = _customer_headers(db)
    response = client.get(f"/api/v1/orders/{order_id}", headers=other_headers)
    assert response.status_code == 403


def test_get_order_admin_can_view_any_order(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    owner_headers = _customer_headers(db)
    _add_to_cart(client, owner_headers, product.id)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=owner_headers).json()["data"]["id"]

    admin_headers = _admin_headers(db)
    response = client.get(f"/api/v1/orders/{order_id}", headers=admin_headers)
    assert response.status_code == 200


def test_get_order_not_found_returns_404(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    response = client.get("/api/v1/orders/999999", headers=headers)
    assert response.status_code == 404


def test_cancel_order_other_customer_gets_403(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    owner_headers = _customer_headers(db)
    _add_to_cart(client, owner_headers, product.id)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=owner_headers).json()["data"]["id"]

    other_headers = _customer_headers(db)
    response = client.put(f"/api/v1/orders/{order_id}/cancel", headers=other_headers)
    assert response.status_code == 403


def test_list_my_orders_only_shows_own_orders(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=10)
    headers_a = _customer_headers(db)
    headers_b = _customer_headers(db)
    _add_to_cart(client, headers_a, product.id)
    client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers_a)

    response = client.get("/api/v1/orders", headers=headers_b)
    assert response.json()["data"]["total"] == 0


# ---- Cancel: hoàn kho, chỉ cho hủy khi pending ----


def test_cancel_order_restocks_and_sets_cancelled(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=10)
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id, quantity=4)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers).json()["data"]["id"]

    db.commit()
    assert db.get(Product, product.id).stock_quantity == 6

    response = client.put(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "cancelled"

    db.commit()
    assert db.get(Product, product.id).stock_quantity == 10  # hoàn kho đầy đủ


def test_cancel_order_twice_returns_400(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers).json()["data"]["id"]

    client.put(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    second = client.put(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert second.status_code == 400


def test_cancel_order_not_pending_returns_400(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers).json()["data"]["id"]

    # db.commit() trước - đóng snapshot REPEATABLE READ cũ (từ
    # _create_category/_create_product ở trên) để thấy đúng order vừa tạo
    # qua session KHÁC (client) - xem giải thích tương tự ở test_product.py.
    db.commit()
    order = db.get(Order, order_id)
    order.status = OrderStatus.shipping
    db.commit()

    response = client.put(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert response.status_code == 400


# ---- Admin: GET /orders/admin, PUT /orders/{id}/status ----


def test_list_all_orders_requires_admin(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    response = client.get("/api/v1/orders/admin", headers=headers)
    assert response.status_code == 403


def test_list_all_orders_shows_every_user(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=10)
    headers_a = _customer_headers(db)
    headers_b = _customer_headers(db)
    _add_to_cart(client, headers_a, product.id)
    client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers_a)
    _add_to_cart(client, headers_b, product.id)
    client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers_b)

    admin_headers = _admin_headers(db)
    response = client.get("/api/v1/orders/admin", headers=admin_headers)
    assert response.json()["data"]["total"] == 2


def test_list_all_orders_filter_by_status(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=10)
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers).json()["data"]["id"]
    client.put(f"/api/v1/orders/{order_id}/cancel", headers=headers)

    admin_headers = _admin_headers(db)
    pending = client.get("/api/v1/orders/admin", params={"status": "pending"}, headers=admin_headers)
    assert pending.json()["data"]["total"] == 0
    cancelled = client.get("/api/v1/orders/admin", params={"status": "cancelled"}, headers=admin_headers)
    assert cancelled.json()["data"]["total"] == 1


def test_update_order_status_requires_admin(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers).json()["data"]["id"]

    response = client.put(f"/api/v1/orders/{order_id}/status", json={"status": "confirmed"}, headers=headers)
    assert response.status_code == 403


def test_update_order_status_to_confirmed(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers).json()["data"]["id"]

    admin_headers = _admin_headers(db)
    response = client.put(f"/api/v1/orders/{order_id}/status", json={"status": "confirmed"}, headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "confirmed"


def test_update_order_status_to_cancelled_restocks(client: TestClient, db: Session) -> None:
    """Admin hủy hộ qua PUT .../status (không phải PUT .../cancel) - CŨNG
    phải hoàn kho, nhất quán với đường hủy của Customer."""
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=10)
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id, quantity=3)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers).json()["data"]["id"]

    db.commit()
    assert db.get(Product, product.id).stock_quantity == 7

    admin_headers = _admin_headers(db)
    response = client.put(f"/api/v1/orders/{order_id}/status", json={"status": "cancelled"}, headers=admin_headers)
    assert response.status_code == 200

    db.commit()
    assert db.get(Product, product.id).stock_quantity == 10


def test_update_order_status_skips_step_returns_400(client: TestClient, db: Session) -> None:
    """State machine (task 3.4.2) - "pending" không được nhảy thẳng sang
    "delivered", phải qua "confirmed" -> "shipping" trước."""
    category = _create_category(db)
    product = _create_product(db, category.id)
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers).json()["data"]["id"]

    admin_headers = _admin_headers(db)
    response = client.put(f"/api/v1/orders/{order_id}/status", json={"status": "delivered"}, headers=admin_headers)
    assert response.status_code == 400
    assert "pending" in response.json()["message"]


def test_update_order_status_from_terminal_state_returns_400(client: TestClient, db: Session) -> None:
    """"delivered"/"cancelled" là trạng thái CUỐI - không chuyển tiếp được
    nữa qua endpoint thường (task 3.4.2 state machine)."""
    category = _create_category(db)
    product = _create_product(db, category.id)
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers).json()["data"]["id"]

    admin_headers = _admin_headers(db)
    client.put(f"/api/v1/orders/{order_id}/status", json={"status": "cancelled"}, headers=admin_headers)

    response = client.put(f"/api/v1/orders/{order_id}/status", json={"status": "confirmed"}, headers=admin_headers)
    assert response.status_code == 400
    assert "cuối" in response.json()["message"]


def test_update_order_status_full_valid_chain_succeeds(client: TestClient, db: Session) -> None:
    """Đối chứng: chuỗi transition HỢP LỆ đầy đủ (pending -> confirmed ->
    shipping -> delivered) phải đi qua trót lọt, state machine không chặn
    nhầm đường đi đúng."""
    category = _create_category(db)
    product = _create_product(db, category.id)
    headers = _customer_headers(db)
    _add_to_cart(client, headers, product.id)
    order_id = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers).json()["data"]["id"]

    admin_headers = _admin_headers(db)
    for next_status in ("confirmed", "shipping", "delivered"):
        response = client.put(
            f"/api/v1/orders/{order_id}/status", json={"status": next_status}, headers=admin_headers
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["status"] == next_status
