"""Test API Review (task "Hoàn thiện review sản phẩm") - end-to-end qua HTTP
thật, MySQL THẬT (mua hàng/đơn hàng) + MongoDB THẬT (`mongo_db` fixture,
database test riêng, xem tests/conftest.py) - KHÔNG mock tầng Mongo (khác
`test_chat_service.py`, nơi mock vì trọng tâm là wiring/streaming, không phải
query/unique-index thật) vì cốt lõi của tính năng này CHÍNH LÀ hành vi
aggregation/unique-index thật của MongoDB - mock sẽ không phát hiện được lỗi
query/index sai.

Đơn hàng `delivered` được tạo TRỰC TIẾP qua `db` fixture (insert thẳng
Order/OrderItem), KHÔNG đi qua toàn bộ luồng checkout + state machine
pending -> confirmed -> shipping -> delivered - việc đó đã test riêng ở
test_order.py, ở đây chỉ cần CÓ SẴN 1 đơn delivered để test nghiệp vụ review.
"""

from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.category import Category
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User, UserRole


def _create_category(db: Session) -> Category:
    category = Category(name="Danh mục", slug=f"cat-{datetime.now().timestamp()}")
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _create_product(db: Session, category_id: int | None = None) -> Product:
    if category_id is None:
        category_id = _create_category(db).id
    product = Product(
        category_id=category_id,
        name="Bình gốm thủ công",
        slug=f"sp-{datetime.now().timestamp()}",
        price=Decimal("150000"),
        stock_quantity=10,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _create_user(db: Session, *, role: UserRole = UserRole.customer, is_active: bool = True) -> User:
    user = User(
        email=f"{role.value}-{datetime.now().timestamp()}@example.com",
        password_hash=hash_password("password123"),
        full_name="Nguyễn Văn A",
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _headers_for(user: User) -> dict:
    token = create_access_token(user_id=user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _create_order(
    db: Session,
    *,
    user: User,
    product: Product,
    status: OrderStatus = OrderStatus.delivered,
    quantity: int = 1,
) -> Order:
    order = Order(
        user_id=user.id,
        status=status,
        total_amount=product.price * quantity,
        shipping_name=user.full_name,
        shipping_address="123 Đường ABC",
        shipping_phone="0900000000",
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    db.add(
        OrderItem(
            order_id=order.id,
            product_id=product.id,
            product_name=product.name,
            quantity=quantity,
            price_at_purchase=product.price,
        )
    )
    db.commit()
    return order


# ---- POST /products/{product_id}/reviews ----


def test_create_review_success(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    user = _create_user(db)
    order = _create_order(db, user=user, product=product)

    response = client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"order_id": order.id, "rating": 5, "comment": "Rất đẹp, đóng gói cẩn thận"},
        headers=_headers_for(user),
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["rating"] == 5
    assert data["comment"] == "Rất đẹp, đóng gói cẩn thận"
    assert data["product_id"] == product.id
    assert data["user_id"] == user.id
    assert data["user_name"] == user.full_name
    assert data["order_id"] == order.id
    assert data["is_verified_purchase"] is True
    assert "is_deleted" not in data  # nội bộ, không lộ ra response công khai


def test_create_review_product_not_found_returns_404(client: TestClient, db: Session) -> None:
    user = _create_user(db)
    response = client.post(
        "/api/v1/products/999999/reviews",
        json={"order_id": 1, "rating": 5},
        headers=_headers_for(user),
    )
    assert response.status_code == 404


def test_create_review_requires_customer_role(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    admin = _create_user(db, role=UserRole.admin)

    response = client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"order_id": 1, "rating": 5},
        headers=_headers_for(admin),
    )
    assert response.status_code == 403


def test_create_review_order_not_owned_by_user_returns_400(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    owner = _create_user(db)
    other = _create_user(db)
    order = _create_order(db, user=owner, product=product)

    response = client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"order_id": order.id, "rating": 4},
        headers=_headers_for(other),
    )
    assert response.status_code == 400
    assert "không tìm thấy" in response.json()["message"].lower() or "không tìm thấy" in response.text.lower()


def test_create_review_order_not_delivered_returns_400(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    user = _create_user(db)
    order = _create_order(db, user=user, product=product, status=OrderStatus.shipping)

    response = client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"order_id": order.id, "rating": 4},
        headers=_headers_for(user),
    )
    assert response.status_code == 400
    assert "giao thành công" in response.json()["message"]


def test_create_review_order_missing_product_returns_400(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product_a = _create_product(db, category.id)
    product_b = _create_product(db, category.id)
    user = _create_user(db)
    # Đơn delivered THẬT, nhưng chỉ chứa product_a - review product_b phải bị chặn.
    order = _create_order(db, user=user, product=product_a)

    response = client.post(
        f"/api/v1/products/{product_b.id}/reviews",
        json={"order_id": order.id, "rating": 4},
        headers=_headers_for(user),
    )
    assert response.status_code == 400
    assert "không chứa sản phẩm" in response.json()["message"]


def test_create_review_duplicate_returns_409(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    user = _create_user(db)
    order = _create_order(db, user=user, product=product)
    headers = _headers_for(user)
    payload = {"order_id": order.id, "rating": 5, "comment": "Tốt"}

    first = client.post(f"/api/v1/products/{product.id}/reviews", json=payload, headers=headers)
    assert first.status_code == 201, first.text

    second = client.post(f"/api/v1/products/{product.id}/reviews", json=payload, headers=headers)
    assert second.status_code == 409


def test_create_review_same_product_different_order_allowed(client: TestClient, db: Session) -> None:
    """Unique index (user_id, order_id, product_id) CHO PHÉP review lại cùng
    sản phẩm nếu mua ở đơn hàng KHÁC (xem docstring app/schemas/review.py)."""
    category = _create_category(db)
    product = _create_product(db, category.id)
    user = _create_user(db)
    order_a = _create_order(db, user=user, product=product)
    order_b = _create_order(db, user=user, product=product)
    headers = _headers_for(user)

    first = client.post(
        f"/api/v1/products/{product.id}/reviews", json={"order_id": order_a.id, "rating": 5}, headers=headers
    )
    assert first.status_code == 201

    second = client.post(
        f"/api/v1/products/{product.id}/reviews", json={"order_id": order_b.id, "rating": 3}, headers=headers
    )
    assert second.status_code == 201


def test_create_review_invalid_rating_returns_422(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    user = _create_user(db)
    order = _create_order(db, user=user, product=product)

    response = client.post(
        f"/api/v1/products/{product.id}/reviews",
        json={"order_id": order.id, "rating": 6},
        headers=_headers_for(user),
    )
    assert response.status_code == 422


# ---- GET /products/{product_id}/reviews ----


def test_list_product_reviews_returns_average_rating_and_total(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    ratings = [5, 3, 4]
    for rating in ratings:
        user = _create_user(db)
        order = _create_order(db, user=user, product=product)
        client.post(
            f"/api/v1/products/{product.id}/reviews",
            json={"order_id": order.id, "rating": rating},
            headers=_headers_for(user),
        )

    response = client.get(f"/api/v1/products/{product.id}/reviews")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 3
    assert data["average_rating"] == round(sum(ratings) / len(ratings), 1)
    assert len(data["items"]) == 3
    # sort mới nhất trước.
    assert data["items"][0]["rating"] == 4


def test_list_product_reviews_empty_has_no_average(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)

    response = client.get(f"/api/v1/products/{product.id}/reviews")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 0
    assert data["average_rating"] is None
    assert data["items"] == []


def test_list_product_reviews_pagination(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    for _ in range(3):
        user = _create_user(db)
        order = _create_order(db, user=user, product=product)
        client.post(
            f"/api/v1/products/{product.id}/reviews", json={"order_id": order.id, "rating": 5}, headers=_headers_for(user)
        )

    page1 = client.get(f"/api/v1/products/{product.id}/reviews", params={"page": 1, "page_size": 2})
    assert page1.json()["data"]["total_pages"] == 2
    assert len(page1.json()["data"]["items"]) == 2

    page2 = client.get(f"/api/v1/products/{product.id}/reviews", params={"page": 2, "page_size": 2})
    assert len(page2.json()["data"]["items"]) == 1


def test_list_product_reviews_hides_soft_deleted(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    user = _create_user(db)
    order = _create_order(db, user=user, product=product)
    create_response = client.post(
        f"/api/v1/products/{product.id}/reviews", json={"order_id": order.id, "rating": 5}, headers=_headers_for(user)
    )
    review_id = create_response.json()["data"]["id"]

    admin = _create_user(db, role=UserRole.admin)
    delete_response = client.delete(f"/api/v1/reviews/{review_id}", headers=_headers_for(admin))
    assert delete_response.status_code == 200

    response = client.get(f"/api/v1/products/{product.id}/reviews")
    data = response.json()["data"]
    assert data["total"] == 0
    assert data["average_rating"] is None


def test_list_product_reviews_product_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/products/999999/reviews")
    assert response.status_code == 404


# ---- DELETE /reviews/{review_id} ----


def test_delete_review_requires_admin(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    user = _create_user(db)
    order = _create_order(db, user=user, product=product)
    review_id = client.post(
        f"/api/v1/products/{product.id}/reviews", json={"order_id": order.id, "rating": 5}, headers=_headers_for(user)
    ).json()["data"]["id"]

    response = client.delete(f"/api/v1/reviews/{review_id}", headers=_headers_for(user))
    assert response.status_code == 403


def test_delete_review_not_found_returns_404(client: TestClient, db: Session) -> None:
    admin = _create_user(db, role=UserRole.admin)
    response = client.delete("/api/v1/reviews/000000000000000000000000", headers=_headers_for(admin))
    assert response.status_code == 404


def test_delete_review_malformed_id_returns_404(client: TestClient, db: Session) -> None:
    admin = _create_user(db, role=UserRole.admin)
    response = client.delete("/api/v1/reviews/not-a-valid-object-id", headers=_headers_for(admin))
    assert response.status_code == 404


def test_delete_review_twice_returns_404_second_time(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    user = _create_user(db)
    order = _create_order(db, user=user, product=product)
    review_id = client.post(
        f"/api/v1/products/{product.id}/reviews", json={"order_id": order.id, "rating": 5}, headers=_headers_for(user)
    ).json()["data"]["id"]
    admin = _create_user(db, role=UserRole.admin)

    first = client.delete(f"/api/v1/reviews/{review_id}", headers=_headers_for(admin))
    assert first.status_code == 200
    second = client.delete(f"/api/v1/reviews/{review_id}", headers=_headers_for(admin))
    assert second.status_code == 404


# ---- GET /reviews (Admin) ----


def test_list_reviews_admin_requires_admin(client: TestClient, db: Session) -> None:
    user = _create_user(db)
    response = client.get("/api/v1/reviews", headers=_headers_for(user))
    assert response.status_code == 403


def test_list_reviews_admin_shows_deleted_and_active_by_default(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    user = _create_user(db)
    order = _create_order(db, user=user, product=product)
    review_id = client.post(
        f"/api/v1/products/{product.id}/reviews", json={"order_id": order.id, "rating": 5}, headers=_headers_for(user)
    ).json()["data"]["id"]
    admin = _create_user(db, role=UserRole.admin)
    client.delete(f"/api/v1/reviews/{review_id}", headers=_headers_for(admin))

    response = client.get("/api/v1/reviews", headers=_headers_for(admin))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["is_deleted"] is True
    assert data["items"][0]["product_name"] == product.name


def test_list_reviews_admin_filter_by_is_deleted(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    user = _create_user(db)
    order = _create_order(db, user=user, product=product)
    client.post(
        f"/api/v1/products/{product.id}/reviews", json={"order_id": order.id, "rating": 5}, headers=_headers_for(user)
    )
    admin = _create_user(db, role=UserRole.admin)

    active_only = client.get("/api/v1/reviews", params={"is_deleted": False}, headers=_headers_for(admin))
    assert active_only.json()["data"]["total"] == 1

    deleted_only = client.get("/api/v1/reviews", params={"is_deleted": True}, headers=_headers_for(admin))
    assert deleted_only.json()["data"]["total"] == 0


def test_list_reviews_admin_filter_by_product_id(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product_a = _create_product(db, category.id)
    product_b = _create_product(db, category.id)
    user = _create_user(db)
    order_a = _create_order(db, user=user, product=product_a)
    order_b = _create_order(db, user=user, product=product_b)
    client.post(
        f"/api/v1/products/{product_a.id}/reviews", json={"order_id": order_a.id, "rating": 5}, headers=_headers_for(user)
    )
    client.post(
        f"/api/v1/products/{product_b.id}/reviews", json={"order_id": order_b.id, "rating": 3}, headers=_headers_for(user)
    )
    admin = _create_user(db, role=UserRole.admin)

    response = client.get("/api/v1/reviews", params={"product_id": product_a.id}, headers=_headers_for(admin))
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["product_id"] == product_a.id
