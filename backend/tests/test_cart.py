"""Test API Cart (task 3.4.2) - end-to-end qua HTTP thật, MySQL thật."""

from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.category import Category
from app.models.product import Product
from app.models.user import User, UserRole


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
        slug=f"sp-{datetime.now().timestamp()}",
        price=Decimal(price),
        stock_quantity=stock_quantity,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _customer_headers(db: Session) -> dict:
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
    token = create_access_token(user_id=user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


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
    token = create_access_token(user_id=user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def test_get_empty_cart(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    response = client.get("/api/v1/cart", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"] == {"items": [], "total_amount": "0"}


def test_add_item_to_cart(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=10, price="50000")
    headers = _customer_headers(db)

    response = client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 2}, headers=headers)
    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["subtotal"] == "100000.00"
    assert data["total_amount"] == "100000.00"


def test_add_same_product_twice_accumulates_quantity(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=10)
    headers = _customer_headers(db)

    client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 2}, headers=headers)
    response = client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 3}, headers=headers)

    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["items"]) == 1  # KHÔNG tạo dòng mới - cộng dồn
    assert data["items"][0]["quantity"] == 5


def test_add_item_exceeding_stock_returns_400(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=3)
    headers = _customer_headers(db)

    response = client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 5}, headers=headers)
    assert response.status_code == 400


def test_add_inactive_product_returns_400(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    product.is_active = False
    db.commit()
    headers = _customer_headers(db)

    response = client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers)
    assert response.status_code == 400


def test_add_unknown_product_returns_400(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    response = client.post("/api/v1/cart/items", json={"product_id": 999999, "quantity": 1}, headers=headers)
    assert response.status_code == 400


def test_update_cart_item_quantity(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=10)
    headers = _customer_headers(db)
    created = client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers)
    item_id = created.json()["data"]["items"][0]["id"]

    response = client.put(f"/api/v1/cart/items/{item_id}", json={"quantity": 4}, headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["items"][0]["quantity"] == 4


def test_update_cart_item_exceeding_stock_returns_400(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id, stock_quantity=3)
    headers = _customer_headers(db)
    created = client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers)
    item_id = created.json()["data"]["items"][0]["id"]

    response = client.put(f"/api/v1/cart/items/{item_id}", json={"quantity": 10}, headers=headers)
    assert response.status_code == 400


def test_update_cart_item_not_owned_returns_404(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    owner_headers = _customer_headers(db)
    created = client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=owner_headers)
    item_id = created.json()["data"]["items"][0]["id"]

    other_headers = _customer_headers(db)
    response = client.put(f"/api/v1/cart/items/{item_id}", json={"quantity": 2}, headers=other_headers)
    assert response.status_code == 404


def test_remove_cart_item(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    headers = _customer_headers(db)
    created = client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers)
    item_id = created.json()["data"]["items"][0]["id"]

    response = client.delete(f"/api/v1/cart/items/{item_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["items"] == []


def test_clear_cart(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product_a = _create_product(db, category.id)
    product_b = _create_product(db, category.id)
    headers = _customer_headers(db)
    client.post("/api/v1/cart/items", json={"product_id": product_a.id, "quantity": 1}, headers=headers)
    client.post("/api/v1/cart/items", json={"product_id": product_b.id, "quantity": 1}, headers=headers)

    response = client.delete("/api/v1/cart", headers=headers)
    assert response.status_code == 200

    cart = client.get("/api/v1/cart", headers=headers)
    assert cart.json()["data"]["items"] == []


def test_cart_requires_customer_role(client: TestClient, db: Session) -> None:
    admin_headers = _admin_headers(db)
    response = client.get("/api/v1/cart", headers=admin_headers)
    assert response.status_code == 403


def test_cart_isolated_per_user(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    product = _create_product(db, category.id)
    headers_a = _customer_headers(db)
    headers_b = _customer_headers(db)

    client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers_a)

    cart_b = client.get("/api/v1/cart", headers=headers_b)
    assert cart_b.json()["data"]["items"] == []
