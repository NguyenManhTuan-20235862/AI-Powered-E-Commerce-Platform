"""Test API Category (`GET /categories` task 4.2.1, CRUD Admin) - end-to-end
qua HTTP thật, MySQL thật.
"""

from datetime import datetime
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.category import Category
from app.models.product import Product
from app.models.user import User, UserRole


def _create_category(db: Session, name: str, **overrides) -> Category:
    fields = {"name": name, "slug": f"cat-{name}-{datetime.now().timestamp()}", **overrides}
    category = Category(**fields)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _create_product(db: Session, category_id: int, name: str = "Sản phẩm test") -> Product:
    product = Product(
        category_id=category_id,
        name=name,
        slug=f"sp-{datetime.now().timestamp()}",
        price=Decimal("100000"),
        stock_quantity=5,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


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


def test_list_categories_empty(client: TestClient) -> None:
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_list_categories_returns_created_categories_sorted_by_name(client: TestClient, db: Session) -> None:
    _create_category(db, "Vải dệt")
    _create_category(db, "Gốm sứ")

    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    data = response.json()["data"]
    names = [item["name"] for item in data]
    assert names == sorted(names)
    assert "Gốm sứ" in names
    assert "Vải dệt" in names


def test_list_categories_id_is_int_not_string(client: TestClient, db: Session) -> None:
    """Guard cho bug đã có ở ProductRead cũ (docs/KNOWN_TODOS.md #14) -
    CategoryRead.id PHẢI là int (khớp BigInteger thật của model), không phải
    str như schema cũ trước khi sửa ở task 4.2.1."""
    category = _create_category(db, "Trang sức")

    response = client.get("/api/v1/categories")
    data = response.json()["data"]
    match = next(item for item in data if item["id"] == category.id)
    assert isinstance(match["id"], int)


# ---- POST /categories ----


def test_create_category_requires_admin(client: TestClient, db: Session) -> None:
    headers = _customer_headers(db)
    response = client.post("/api/v1/categories", json={"name": "Đồ chơi"}, headers=headers)
    assert response.status_code == 403


def test_create_category_without_auth_returns_401(client: TestClient) -> None:
    response = client.post("/api/v1/categories", json={"name": "Đồ chơi"})
    assert response.status_code == 401


def test_create_category_auto_generates_slug(client: TestClient, db: Session) -> None:
    headers = _admin_headers(db)
    response = client.post("/api/v1/categories", json={"name": "Đồ Gia Dụng Cao Cấp"}, headers=headers)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["slug"] == "do-gia-dung-cao-cap"
    assert data["parent_id"] is None


def test_create_category_duplicate_name_gets_unique_slug_suffix(client: TestClient, db: Session) -> None:
    headers = _admin_headers(db)
    first = client.post("/api/v1/categories", json={"name": "Sách"}, headers=headers).json()["data"]
    second = client.post("/api/v1/categories", json={"name": "Sách"}, headers=headers).json()["data"]

    assert first["slug"] == "sach"
    assert second["slug"] == "sach-2"


def test_create_category_explicit_slug_still_normalized(client: TestClient, db: Session) -> None:
    headers = _admin_headers(db)
    response = client.post(
        "/api/v1/categories", json={"name": "Làm đẹp", "slug": "Làm Đẹp Cao Cấp!!"}, headers=headers
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["slug"] == "lam-dep-cao-cap"


def test_create_category_with_valid_parent(client: TestClient, db: Session) -> None:
    parent = _create_category(db, "Điện tử")
    headers = _admin_headers(db)
    response = client.post(
        "/api/v1/categories", json={"name": "Điện thoại", "parent_id": parent.id}, headers=headers
    )
    assert response.status_code == 201, response.text
    assert response.json()["data"]["parent_id"] == parent.id


def test_create_category_unknown_parent_returns_400(client: TestClient, db: Session) -> None:
    headers = _admin_headers(db)
    response = client.post(
        "/api/v1/categories", json={"name": "Điện thoại", "parent_id": 999999}, headers=headers
    )
    assert response.status_code == 400


# ---- PUT /categories/{id} ----


def test_update_category_requires_admin(client: TestClient, db: Session) -> None:
    category = _create_category(db, "Nhà cửa")
    headers = _customer_headers(db)
    response = client.put(f"/api/v1/categories/{category.id}", json={"name": "Đổi tên"}, headers=headers)
    assert response.status_code == 403


def test_update_category_not_found_returns_404(client: TestClient, db: Session) -> None:
    headers = _admin_headers(db)
    response = client.put("/api/v1/categories/999999", json={"name": "X"}, headers=headers)
    assert response.status_code == 404


def test_update_category_partial_update_keeps_other_fields(client: TestClient, db: Session) -> None:
    category = _create_category(db, "Làm đẹp", description="Mô tả gốc")
    headers = _admin_headers(db)

    response = client.put(
        f"/api/v1/categories/{category.id}", json={"description": "Mô tả mới"}, headers=headers
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["description"] == "Mô tả mới"
    assert data["name"] == "Làm đẹp"  # không đổi vì không truyền


def test_update_category_explicit_slug_regenerated_excluding_self(client: TestClient, db: Session) -> None:
    """Đổi slug về ĐÚNG slug hiện tại của chính nó KHÔNG được coi là trùng
    (exclude_category_id) - phải giữ nguyên, không bị tự thêm hậu tố -2."""
    category = _create_category(db, "Đồ chơi")
    headers = _admin_headers(db)

    response = client.put(
        f"/api/v1/categories/{category.id}", json={"slug": "Do Choi"}, headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["slug"] == "do-choi"


def test_update_category_slug_colliding_with_another_gets_suffix(client: TestClient, db: Session) -> None:
    _create_category(db, "Sách", slug="sach-cu")
    target = _create_category(db, "Đồ chơi")
    headers = _admin_headers(db)

    response = client.put(
        f"/api/v1/categories/{target.id}", json={"slug": "sach-cu"}, headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["slug"] == "sach-cu-2"


def test_update_category_unknown_parent_returns_400(client: TestClient, db: Session) -> None:
    category = _create_category(db, "Điện thoại")
    headers = _admin_headers(db)
    response = client.put(
        f"/api/v1/categories/{category.id}", json={"parent_id": 999999}, headers=headers
    )
    assert response.status_code == 400


def test_update_category_valid_parent_change(client: TestClient, db: Session) -> None:
    parent = _create_category(db, "Điện tử")
    child = _create_category(db, "Điện thoại")
    headers = _admin_headers(db)

    response = client.put(
        f"/api/v1/categories/{child.id}", json={"parent_id": parent.id}, headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["parent_id"] == parent.id


def test_update_category_clear_parent_by_explicit_null(client: TestClient, db: Session) -> None:
    parent = _create_category(db, "Điện tử")
    child = _create_category(db, "Điện thoại", parent_id=parent.id)
    headers = _admin_headers(db)

    response = client.put(
        f"/api/v1/categories/{child.id}", json={"parent_id": None}, headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["parent_id"] is None


def test_update_category_self_parent_direct_cycle_returns_400(client: TestClient, db: Session) -> None:
    """A tự đặt chính nó làm cha (vòng lặp trực tiếp, 1 bước)."""
    category = _create_category(db, "Điện tử")
    headers = _admin_headers(db)

    response = client.put(
        f"/api/v1/categories/{category.id}", json={"parent_id": category.id}, headers=headers
    )
    assert response.status_code == 400


def test_update_category_indirect_cycle_returns_400(client: TestClient, db: Session) -> None:
    """A hiện là cha của B - đổi A thành con của B tạo vòng lặp gián tiếp
    (A -> B -> A). Đây là phép thử QUAN TRỌNG NHẤT cho thuật toán tổng quát
    (không chỉ bắt được trường hợp "cha của chính mình")."""
    a = _create_category(db, "Điện tử")
    b = _create_category(db, "Điện thoại", parent_id=a.id)
    headers = _admin_headers(db)

    response = client.put(f"/api/v1/categories/{a.id}", json={"parent_id": b.id}, headers=headers)
    assert response.status_code == 400


def test_update_category_deep_indirect_cycle_returns_400(client: TestClient, db: Session) -> None:
    """A -> B -> C (C con của B, B con của A) - đổi A thành con của C tạo
    vòng lặp gián tiếp qua 2 cấp trung gian (A -> C -> B -> A)."""
    a = _create_category(db, "Cấp 1")
    b = _create_category(db, "Cấp 2", parent_id=a.id)
    c = _create_category(db, "Cấp 3", parent_id=b.id)
    headers = _admin_headers(db)

    response = client.put(f"/api/v1/categories/{a.id}", json={"parent_id": c.id}, headers=headers)
    assert response.status_code == 400


def test_update_category_reparent_grandchild_to_grandparent_is_not_a_cycle(client: TestClient, db: Session) -> None:
    """Đối chứng: C (cháu của A qua B) chuyển thành con TRỰC TIẾP của A -
    KHÔNG phải vòng lặp (A vẫn là tổ tiên hợp lệ, chỉ đổi độ sâu), phải cho
    phép - test này đảm bảo thuật toán không chặn nhầm trường hợp hợp lệ."""
    a = _create_category(db, "Cấp 1")
    b = _create_category(db, "Cấp 2", parent_id=a.id)
    c = _create_category(db, "Cấp 3", parent_id=b.id)
    headers = _admin_headers(db)

    response = client.put(f"/api/v1/categories/{c.id}", json={"parent_id": a.id}, headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["data"]["parent_id"] == a.id


# ---- DELETE /categories/{id} ----


def test_delete_category_requires_admin(client: TestClient, db: Session) -> None:
    category = _create_category(db, "Nhà cửa")
    headers = _customer_headers(db)
    response = client.delete(f"/api/v1/categories/{category.id}", headers=headers)
    assert response.status_code == 403


def test_delete_category_not_found_returns_404(client: TestClient, db: Session) -> None:
    headers = _admin_headers(db)
    response = client.delete("/api/v1/categories/999999", headers=headers)
    assert response.status_code == 404


def test_delete_category_with_products_returns_409(client: TestClient, db: Session) -> None:
    category = _create_category(db, "Sách")
    _create_product(db, category.id)
    _create_product(db, category.id)
    headers = _admin_headers(db)

    response = client.delete(f"/api/v1/categories/{category.id}", headers=headers)
    assert response.status_code == 409
    assert "2 sản phẩm" in response.json()["message"]


def test_delete_category_with_child_categories_returns_409(client: TestClient, db: Session) -> None:
    parent = _create_category(db, "Điện tử")
    _create_category(db, "Điện thoại", parent_id=parent.id)
    headers = _admin_headers(db)

    response = client.delete(f"/api/v1/categories/{parent.id}", headers=headers)
    assert response.status_code == 409
    assert "1 danh mục con" in response.json()["message"]


def test_delete_category_success_removes_from_db(client: TestClient, db: Session) -> None:
    category = _create_category(db, "Đồ chơi")
    headers = _admin_headers(db)

    response = client.delete(f"/api/v1/categories/{category.id}", headers=headers)
    assert response.status_code == 200, response.text

    list_response = client.get("/api/v1/categories")
    ids = [item["id"] for item in list_response.json()["data"]]
    assert category.id not in ids


def test_delete_category_after_removing_products_succeeds(client: TestClient, db: Session) -> None:
    """Đối chứng cho test_delete_category_with_products_returns_409 - xóa
    sản phẩm (soft-delete KHÔNG đổi category_id, nên xóa hẳn dòng
    order_items/product qua DB thẳng trong test để mô phỏng "đã dọn sạch")
    rồi xóa category phải thành công."""
    category = _create_category(db, "Sách")
    product = _create_product(db, category.id)
    db.delete(product)
    db.commit()
    headers = _admin_headers(db)

    response = client.delete(f"/api/v1/categories/{category.id}", headers=headers)
    assert response.status_code == 200, response.text
