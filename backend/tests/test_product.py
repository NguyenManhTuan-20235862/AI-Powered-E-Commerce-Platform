"""Test API CRUD Product (task 3.4.1) - end-to-end qua HTTP thật, MySQL +
Redis thật (không mock, cùng triết lý đã dùng xuyên suốt dự án).
"""

import base64
from datetime import datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.cache import invalidate_by_prefix
from app.core.security import create_access_token, hash_password
from app.models.category import Category
from app.models.user import User, UserRole
from app.services.product_service import PRODUCT_LIST_CACHE_PREFIX

# PNG 1x1 hợp lệ (transparent pixel) - đủ để pass content-type + đọc được
# bytes thật, không cần ảnh thật cho mục đích test upload.
_TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


@pytest.fixture(autouse=True)
def _clean_product_cache(redis_client):
    """Tự dọn cache `products:list:*` trước VÀ sau mỗi test - key này KHÔNG
    có tiền tố `test:` (đúng quy ước key thật dùng ở production) nên fixture
    `redis_client` dùng chung (tests/conftest.py, chỉ dọn `test:*`) không tự
    dọn được - cần fixture riêng ở đây để tránh cache từ test này rò sang
    test khác (VD test A cache "trang 1 rỗng", test B tạo sản phẩm mới rồi
    kỳ vọng thấy trong trang 1 nhưng lại đọc trúng cache cũ của test A)."""
    invalidate_by_prefix(redis_client, PRODUCT_LIST_CACHE_PREFIX)
    yield
    invalidate_by_prefix(redis_client, PRODUCT_LIST_CACHE_PREFIX)


def _create_category(db: Session, name: str = "Áo thun") -> Category:
    category = Category(name=name, slug=f"cat-{datetime.now().timestamp()}")
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


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


def _create_product(client: TestClient, headers: dict, category_id: int, **overrides) -> dict:
    payload = {
        "category_id": category_id,
        "name": "Áo thun basic",
        "price": "199000",
        "stock_quantity": 10,
        **overrides,
    }
    response = client.post("/api/v1/products", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["data"]


# ---- CRUD cơ bản + quyền Admin/Customer ----


def test_create_product_requires_admin(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    customer_headers = _customer_headers(db)
    response = client.post(
        "/api/v1/products",
        json={"category_id": category.id, "name": "X", "price": "10000", "stock_quantity": 1},
        headers=customer_headers,
    )
    assert response.status_code == 403


def test_create_product_without_auth_returns_401(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    response = client.post(
        "/api/v1/products",
        json={"category_id": category.id, "name": "X", "price": "10000", "stock_quantity": 1},
    )
    assert response.status_code == 401


def test_create_product_unknown_category_returns_400(client: TestClient, db: Session) -> None:
    headers = _admin_headers(db)
    response = client.post(
        "/api/v1/products",
        json={"category_id": 999999, "name": "X", "price": "10000", "stock_quantity": 1},
        headers=headers,
    )
    assert response.status_code == 400


def test_create_product_auto_generates_slug_and_nested_category(client: TestClient, db: Session) -> None:
    category = _create_category(db, name="Điện thoại")
    headers = _admin_headers(db)
    data = _create_product(client, headers, category.id, name="Áo Khoác Nam Đẹp")

    assert data["slug"] == "ao-khoac-nam-dep"
    assert data["category"] == {"id": category.id, "name": "Điện thoại"}
    assert data["stock_quantity"] == 10
    assert data["is_active"] is True


def test_create_product_duplicate_name_gets_unique_slug_suffix(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    headers = _admin_headers(db)
    first = _create_product(client, headers, category.id, name="Áo thun")
    second = _create_product(client, headers, category.id, name="Áo thun")

    assert first["slug"] == "ao-thun"
    assert second["slug"] == "ao-thun-2"


def test_get_product_detail(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    headers = _admin_headers(db)
    created = _create_product(client, headers, category.id)

    response = client.get(f"/api/v1/products/{created['id']}")
    assert response.status_code == 200
    assert response.json()["data"]["id"] == created["id"]


def test_get_product_detail_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/products/999999")
    assert response.status_code == 404


def test_update_product_requires_admin(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    admin_headers = _admin_headers(db)
    created = _create_product(client, admin_headers, category.id)

    customer_headers = _customer_headers(db)
    response = client.put(
        f"/api/v1/products/{created['id']}", json={"name": "Hack"}, headers=customer_headers
    )
    assert response.status_code == 403


def test_update_product_partial_update_keeps_other_fields(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    headers = _admin_headers(db)
    created = _create_product(client, headers, category.id, price="100000")

    response = client.put(
        f"/api/v1/products/{created['id']}", json={"price": "150000"}, headers=headers
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["price"] == "150000.00"
    assert data["name"] == created["name"]  # không đổi vì không truyền


def test_update_product_cannot_change_stock_quantity(client: TestClient, db: Session) -> None:
    """ProductUpdate KHÔNG có field stock_quantity - gửi kèm trong body bị
    Pydantic bỏ qua (extra field mặc định), tồn kho PHẢI giữ nguyên."""
    category = _create_category(db)
    headers = _admin_headers(db)
    created = _create_product(client, headers, category.id, stock_quantity=10)

    response = client.put(
        f"/api/v1/products/{created['id']}",
        json={"name": "Đổi tên", "stock_quantity": 9999},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["stock_quantity"] == 10


def test_update_product_unknown_category_returns_400(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    headers = _admin_headers(db)
    created = _create_product(client, headers, category.id)

    response = client.put(
        f"/api/v1/products/{created['id']}", json={"category_id": 999999}, headers=headers
    )
    assert response.status_code == 400


def test_delete_product_is_soft_delete_not_hard_delete(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    headers = _admin_headers(db)
    created = _create_product(client, headers, category.id)

    delete_response = client.delete(f"/api/v1/products/{created['id']}", headers=headers)
    assert delete_response.status_code == 200

    # Public: sản phẩm đã ẩn -> 404 (không phân biệt "không tồn tại" hay "đã ẩn").
    assert client.get(f"/api/v1/products/{created['id']}").status_code == 404

    # Nhưng bản ghi MySQL vẫn còn thật (soft-delete, KHÔNG xóa cứng) - verify
    # trực tiếp qua DB session, không chỉ tin vào response API.
    from app.models.product import Product

    # db.commit() (không có gì để ghi, chỉ để ĐÓNG transaction REPEATABLE READ
    # đang mở từ _create_category() ở trên - db.refresh() sau db.commit() tự
    # mở lại 1 transaction ngầm) - nếu không, session này vẫn kẹt ở snapshot
    # CŨ (trước khi tạo/xóa sản phẩm qua client, chạy trên session KHÁC) và
    # sẽ không thấy được thay đổi mới dù đã commit thật ở phía kia.
    db.commit()
    row = db.get(Product, created["id"])
    assert row is not None
    assert row.is_active is False

    # Admin vẫn PUT được để kích hoạt lại (is_active=true qua PUT thông thường).
    reactivate = client.put(
        f"/api/v1/products/{created['id']}", json={"is_active": True}, headers=headers
    )
    assert reactivate.status_code == 200
    assert reactivate.json()["data"]["is_active"] is True
    assert client.get(f"/api/v1/products/{created['id']}").status_code == 200


def test_delete_product_requires_admin(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    admin_headers = _admin_headers(db)
    created = _create_product(client, admin_headers, category.id)

    customer_headers = _customer_headers(db)
    response = client.delete(f"/api/v1/products/{created['id']}", headers=customer_headers)
    assert response.status_code == 403


# ---- Danh sách: phân trang, filter, cache ----


def test_list_products_pagination(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    headers = _admin_headers(db)
    for i in range(3):
        _create_product(client, headers, category.id, name=f"SP {i}", price="10000")

    response = client.get("/api/v1/products", params={"page": 1, "page_size": 2})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2
    assert data["total_pages"] == 2

    page2 = client.get("/api/v1/products", params={"page": 2, "page_size": 2}).json()["data"]
    assert len(page2["items"]) == 1


def test_list_products_only_shows_active(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    headers = _admin_headers(db)
    created = _create_product(client, headers, category.id)
    client.delete(f"/api/v1/products/{created['id']}", headers=headers)

    response = client.get("/api/v1/products")
    ids = [item["id"] for item in response.json()["data"]["items"]]
    assert created["id"] not in ids


def test_list_products_filter_by_category(client: TestClient, db: Session) -> None:
    category_a = _create_category(db, name="A")
    category_b = _create_category(db, name="B")
    headers = _admin_headers(db)
    product_a = _create_product(client, headers, category_a.id, name="Trong A")
    _create_product(client, headers, category_b.id, name="Trong B")

    response = client.get("/api/v1/products", params={"category_id": category_a.id})
    items = response.json()["data"]["items"]
    assert {item["id"] for item in items} == {product_a["id"]}


def test_list_products_filter_by_price_range(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    headers = _admin_headers(db)
    cheap = _create_product(client, headers, category.id, name="Rẻ", price="10000")
    _create_product(client, headers, category.id, name="Đắt", price="900000")

    response = client.get("/api/v1/products", params={"max_price": "50000"})
    items = response.json()["data"]["items"]
    assert {item["id"] for item in items} == {cheap["id"]}


def test_list_products_search_by_name(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    headers = _admin_headers(db)
    match = _create_product(client, headers, category.id, name="Áo Khoác Da")
    _create_product(client, headers, category.id, name="Quần Jean")

    response = client.get("/api/v1/products", params={"search": "khoác"})
    items = response.json()["data"]["items"]
    assert {item["id"] for item in items} == {match["id"]}


def test_list_products_cache_hit_returns_same_data_and_skips_new_writes(
    client: TestClient, db: Session
) -> None:
    """Verify cache THẬT hoạt động: gọi lần 1 (miss, query DB) trả 0 sản
    phẩm; tạo thêm sản phẩm KHÔNG qua API (bypass invalidate) để mô phỏng
    "dữ liệu đổi nhưng cache chưa biết"; gọi lại CÙNG key (page 1, không
    filter) - phải vẫn thấy 0 sản phẩm (cache hit, chưa hết TTL) - chứng
    minh response thật sự tới từ Redis, không phải query DB lại.
    """
    category = _create_category(db)

    first = client.get("/api/v1/products", params={"page": 1, "page_size": 20})
    assert first.json()["data"]["total"] == 0

    # Ghi thẳng DB, KHÔNG qua POST /products - cố tình không invalidate cache,
    # để chứng minh lần gọi kế tiếp đọc từ cache (không thấy sản phẩm mới)
    # thay vì query DB lại (sẽ thấy ngay nếu không có cache).
    from app.models.product import Product

    db.add(
        Product(
            category_id=category.id,
            name="Ghi thẳng DB",
            slug="ghi-thang-db",
            price=Decimal("50000"),
            stock_quantity=1,
            is_active=True,
        )
    )
    db.commit()

    second = client.get("/api/v1/products", params={"page": 1, "page_size": 20})
    assert second.json()["data"]["total"] == 0  # vẫn cache hit, chưa thấy sản phẩm mới

    # Nhưng query trực tiếp DB (không qua cache) đã thấy ngay - xác nhận đây
    # đúng là do cache, không phải bug ở query.
    assert db.query(Product).filter(Product.name == "Ghi thẳng DB").count() == 1


def test_create_product_invalidates_list_cache(client: TestClient, db: Session) -> None:
    """Khác test trên: tạo sản phẩm qua ĐÚNG API (POST /products) - PHẢI
    invalidate cache ngay, trang danh sách phải thấy sản phẩm mới NGAY LẬP
    TỨC, không cần đợi hết TTL 5 phút."""
    category = _create_category(db)
    headers = _admin_headers(db)

    before = client.get("/api/v1/products", params={"page": 1, "page_size": 20})
    assert before.json()["data"]["total"] == 0

    _create_product(client, headers, category.id, name="Sản phẩm mới")

    after = client.get("/api/v1/products", params={"page": 1, "page_size": 20})
    assert after.json()["data"]["total"] == 1


# ---- Related products ----


def test_related_products_same_category_excludes_self(client: TestClient, db: Session) -> None:
    category_a = _create_category(db, name="A")
    category_b = _create_category(db, name="B")
    headers = _admin_headers(db)
    anchor = _create_product(client, headers, category_a.id, name="Gốc")
    sibling = _create_product(client, headers, category_a.id, name="Cùng danh mục")
    _create_product(client, headers, category_b.id, name="Khác danh mục")

    response = client.get(f"/api/v1/products/{anchor['id']}/related")
    assert response.status_code == 200
    ids = [item["id"] for item in response.json()["data"]]
    assert ids == [sibling["id"]]


def test_related_products_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/products/999999/related")
    assert response.status_code == 404


# ---- Upload ảnh ----


def test_upload_product_image_success(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    headers = _admin_headers(db)
    created = _create_product(client, headers, category.id)

    response = client.post(
        f"/api/v1/products/{created['id']}/image",
        headers=headers,
        files={"file": ("test.png", _TINY_PNG, "image/png")},
    )
    assert response.status_code == 200
    image_url = response.json()["data"]["image_url"]
    assert image_url.startswith("/api/v1/uploads/products/")

    detail = client.get(f"/api/v1/products/{created['id']}")
    assert detail.json()["data"]["image_url"] == image_url


def test_upload_product_image_rejects_invalid_content_type(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    headers = _admin_headers(db)
    created = _create_product(client, headers, category.id)

    response = client.post(
        f"/api/v1/products/{created['id']}/image",
        headers=headers,
        files={"file": ("test.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


def test_upload_product_image_requires_admin(client: TestClient, db: Session) -> None:
    category = _create_category(db)
    admin_headers = _admin_headers(db)
    created = _create_product(client, admin_headers, category.id)

    customer_headers = _customer_headers(db)
    response = client.post(
        f"/api/v1/products/{created['id']}/image",
        headers=customer_headers,
        files={"file": ("test.png", _TINY_PNG, "image/png")},
    )
    assert response.status_code == 403
