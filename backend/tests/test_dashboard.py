"""Test API Dashboard / Statistics (task 5.3.1) - end-to-end qua HTTP thật,
MySQL thật (cùng convention `test_order.py`).

Tạo Order/OrderItem TRỰC TIẾP qua fixture `db` (không qua `POST /orders`) -
cần kiểm soát CHÍNH XÁC `created_at`/`status` để test logic lọc theo
khoảng ngày + loại trừ "cancelled", điều `POST /orders` không cho làm (luôn
gán `created_at` = lúc gọi API thật, không lùi ngày được).
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password
from app.models.category import Category
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.user import User, UserRole

TODAY = date.today()


@pytest.fixture(autouse=True)
def _cleanup_dashboard_cache(redis_client):
    """Endpoint dashboard cache qua Redis THẬT dùng chung với app (KHÔNG
    phải Redis riêng cho test) với key tiền tố `dashboard:` (không phải
    `test:` - đó là quy ước cho test tự chọn key thủ công như
    `tests/test_cache.py`, khác test này gọi qua HTTP thật nên không tự chọn
    được key). TTL 5 phút tự hết hạn, nhưng dọn NGAY sau mỗi test ở đây cho
    đúng nguyên tắc "dữ liệu test verify phải dọn sạch" (.claude/rules/data-safety.md)
    thay vì để rác cache thật tồn tại tới 5 phút sau khi test đã xong."""
    yield
    keys = redis_client.keys("dashboard:*")
    if keys:
        redis_client.delete(*keys)


def _headers_for(user: User) -> dict:
    token = create_access_token(user_id=user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _create_user(db: Session, *, role: UserRole, created_at: datetime | None = None) -> User:
    user = User(
        email=f"user-{datetime.now().timestamp()}@example.com",
        password_hash=hash_password("password123"),
        full_name="Test User",
        role=role,
        is_active=True,
        **({"created_at": created_at} if created_at is not None else {}),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _admin_headers(db: Session) -> dict:
    return _headers_for(_create_user(db, role=UserRole.admin))


def _create_category(db: Session) -> Category:
    category = Category(name="Danh mục", slug=f"cat-{datetime.now().timestamp()}")
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _create_product(db: Session, category_id: int, *, price: str = "100000") -> Product:
    product = Product(
        category_id=category_id,
        name="Sản phẩm test",
        slug=f"sp-{datetime.now().timestamp()}",
        price=Decimal(price),
        stock_quantity=1000,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _create_order(
    db: Session,
    user_id: int,
    *,
    status: OrderStatus,
    total_amount: str,
    created_at: datetime,
    items: list[tuple[Product, int]] | None = None,
) -> Order:
    """`items`: danh sách (product, quantity) - nếu truyền, tự tạo `order_items`
    tương ứng (giá lấy từ `product.price` tại thời điểm gọi, snapshot đúng
    nguyên tắc `order_items.price_at_purchase`)."""
    order = Order(
        user_id=user_id,
        status=status,
        total_amount=Decimal(total_amount),
        shipping_name="Người nhận",
        shipping_address="Địa chỉ test",
        shipping_phone="0900000000",
        created_at=created_at,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    for product, quantity in items or []:
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


# ---- Quyền truy cập ----


def test_summary_requires_admin_role(client: TestClient, db: Session) -> None:
    customer = _create_user(db, role=UserRole.customer)
    response = client.get("/api/v1/admin/dashboard/summary", headers=_headers_for(customer))
    assert response.status_code == 403


def test_summary_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/admin/dashboard/summary")
    assert response.status_code == 401


# ---- GET /admin/dashboard/summary ----


def test_summary_excludes_cancelled_from_revenue_but_counts_it_in_total_orders(client: TestClient, db: Session) -> None:
    admin_headers = _admin_headers(db)
    customer = _create_user(db, role=UserRole.customer)
    now = datetime.now()

    _create_order(db, customer.id, status=OrderStatus.pending, total_amount="100000", created_at=now)
    _create_order(db, customer.id, status=OrderStatus.confirmed, total_amount="200000", created_at=now)
    _create_order(db, customer.id, status=OrderStatus.delivered, total_amount="300000", created_at=now)
    _create_order(db, customer.id, status=OrderStatus.cancelled, total_amount="999999", created_at=now)

    response = client.get("/api/v1/admin/dashboard/summary", headers=admin_headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    # Doanh thu CHỈ tính 3 đơn không "cancelled" - đơn cancelled 999999 KHÔNG
    # được cộng vào, dù giá trị rất lớn (nếu lẫn vào sẽ lộ ngay qua tổng sai).
    assert Decimal(str(data["total_revenue"])) == Decimal("600000")
    # total_orders đếm CẢ 4 đơn (kể cả cancelled) - chỉ số hoạt động, khác doanh thu.
    assert data["total_orders"] == 4


def test_summary_new_users_counts_only_customer_role_in_range(client: TestClient, db: Session) -> None:
    admin_headers = _admin_headers(db)
    now = datetime.now()

    _create_user(db, role=UserRole.customer, created_at=now)
    _create_user(db, role=UserRole.customer, created_at=now)
    # Admin mới tạo trong CÙNG khoảng - KHÔNG được tính vào "new_users".
    _create_user(db, role=UserRole.admin, created_at=now)

    response = client.get("/api/v1/admin/dashboard/summary", headers=admin_headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    # +1 vì chính admin gọi API (_admin_headers tạo trước) cũng nằm trong
    # khoảng mặc định - CHỈ đếm customer nên vẫn phải LOẠI được, assert đúng
    # số lượng customer thật đã tạo (2), không lẫn admin.
    assert data["new_users"] == 2


def test_summary_default_range_excludes_orders_outside_30_days(client: TestClient, db: Session) -> None:
    admin_headers = _admin_headers(db)
    customer = _create_user(db, role=UserRole.customer)

    _create_order(db, customer.id, status=OrderStatus.delivered, total_amount="100000", created_at=datetime.now())
    # 40 ngày trước - NGOÀI khoảng mặc định 30 ngày, phải bị loại.
    old_date = datetime.now() - timedelta(days=40)
    _create_order(db, customer.id, status=OrderStatus.delivered, total_amount="500000", created_at=old_date)

    response = client.get("/api/v1/admin/dashboard/summary", headers=admin_headers)
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    assert Decimal(str(data["total_revenue"])) == Decimal("100000")
    assert data["total_orders"] == 1


def test_summary_explicit_date_range_includes_old_order(client: TestClient, db: Session) -> None:
    admin_headers = _admin_headers(db)
    customer = _create_user(db, role=UserRole.customer)
    old_date = datetime.now() - timedelta(days=40)
    _create_order(db, customer.id, status=OrderStatus.delivered, total_amount="500000", created_at=old_date)

    response = client.get(
        "/api/v1/admin/dashboard/summary",
        params={"date_from": (TODAY - timedelta(days=45)).isoformat(), "date_to": TODAY.isoformat()},
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert Decimal(str(data["total_revenue"])) == Decimal("500000")


# ---- GET /admin/dashboard/revenue ----


def test_revenue_buckets_by_day_and_fills_zero_for_gap_day(client: TestClient, db: Session) -> None:
    admin_headers = _admin_headers(db)
    customer = _create_user(db, role=UserRole.customer)

    day1 = datetime.combine(TODAY - timedelta(days=2), datetime.min.time().replace(hour=10))
    # Cố tình KHÔNG tạo đơn nào ở TODAY - 1 (ngày giữa) - phải vẫn xuất hiện
    # trong response với revenue=0 (mảng liên tục cho Chart.js).
    day3 = datetime.combine(TODAY, datetime.min.time().replace(hour=10))

    _create_order(db, customer.id, status=OrderStatus.delivered, total_amount="100000", created_at=day1)
    _create_order(db, customer.id, status=OrderStatus.cancelled, total_amount="999999", created_at=day1)
    _create_order(db, customer.id, status=OrderStatus.confirmed, total_amount="300000", created_at=day3)

    response = client.get(
        "/api/v1/admin/dashboard/revenue",
        params={
            "date_from": (TODAY - timedelta(days=2)).isoformat(),
            "date_to": TODAY.isoformat(),
            "interval": "day",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    points = {p["period"]: Decimal(str(p["revenue"])) for p in response.json()["data"]}

    assert len(points) == 3
    assert points[(TODAY - timedelta(days=2)).isoformat()] == Decimal("100000")  # cancelled KHÔNG cộng vào
    assert points[(TODAY - timedelta(days=1)).isoformat()] == Decimal("0")  # ngày trống - điền 0
    assert points[TODAY.isoformat()] == Decimal("300000")


def test_revenue_buckets_by_month(client: TestClient, db: Session) -> None:
    admin_headers = _admin_headers(db)
    customer = _create_user(db, role=UserRole.customer)
    now = datetime.now()

    _create_order(db, customer.id, status=OrderStatus.delivered, total_amount="150000", created_at=now)

    response = client.get(
        "/api/v1/admin/dashboard/revenue",
        params={
            "date_from": (TODAY - timedelta(days=1)).isoformat(),
            "date_to": TODAY.isoformat(),
            "interval": "month",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    points = response.json()["data"]
    assert len(points) == 1
    assert points[0]["period"] == now.strftime("%Y-%m")
    assert Decimal(str(points[0]["revenue"])) == Decimal("150000")


# ---- GET /admin/dashboard/top-products ----


def test_top_products_ranks_by_quantity_by_default(client: TestClient, db: Session) -> None:
    admin_headers = _admin_headers(db)
    customer = _create_user(db, role=UserRole.customer)
    category = _create_category(db)
    now = datetime.now()

    product_a = _create_product(db, category.id, price="100000")  # bán ít, giá cao
    product_b = _create_product(db, category.id, price="10000")  # bán nhiều, giá thấp

    _create_order(
        db, customer.id, status=OrderStatus.delivered, total_amount="200000", created_at=now,
        items=[(product_a, 2)],
    )
    _create_order(
        db, customer.id, status=OrderStatus.confirmed, total_amount="100000", created_at=now,
        items=[(product_b, 10)],
    )
    # Đơn cancelled - order_items của đơn này KHÔNG được tính vào top-products.
    _create_order(
        db, customer.id, status=OrderStatus.cancelled, total_amount="999999", created_at=now,
        items=[(product_a, 999)],
    )

    response = client.get("/api/v1/admin/dashboard/top-products", headers=admin_headers)
    assert response.status_code == 200, response.text
    items = response.json()["data"]

    assert len(items) == 2
    # product_b bán 10 (nhiều hơn product_a bán 2) -> đứng đầu khi sort mặc định (quantity).
    assert items[0]["product_id"] == product_b.id
    assert items[0]["quantity_sold"] == 10
    assert Decimal(str(items[0]["revenue"])) == Decimal("100000")
    assert items[1]["product_id"] == product_a.id
    assert items[1]["quantity_sold"] == 2


def test_top_products_sort_by_revenue(client: TestClient, db: Session) -> None:
    admin_headers = _admin_headers(db)
    customer = _create_user(db, role=UserRole.customer)
    category = _create_category(db)
    now = datetime.now()

    product_a = _create_product(db, category.id, price="100000")  # bán ít nhưng doanh thu cao
    product_b = _create_product(db, category.id, price="10000")  # bán nhiều nhưng doanh thu thấp

    _create_order(
        db, customer.id, status=OrderStatus.delivered, total_amount="200000", created_at=now,
        items=[(product_a, 2)],
    )
    _create_order(
        db, customer.id, status=OrderStatus.confirmed, total_amount="100000", created_at=now,
        items=[(product_b, 10)],
    )

    response = client.get(
        "/api/v1/admin/dashboard/top-products", params={"sort_by": "revenue"}, headers=admin_headers
    )
    assert response.status_code == 200, response.text
    items = response.json()["data"]

    # Đổi tiêu chí sort -> thứ tự PHẢI đảo ngược so với test mặc định (quantity).
    assert items[0]["product_id"] == product_a.id
    assert Decimal(str(items[0]["revenue"])) == Decimal("200000")
    assert items[1]["product_id"] == product_b.id


def test_top_products_respects_limit(client: TestClient, db: Session) -> None:
    admin_headers = _admin_headers(db)
    customer = _create_user(db, role=UserRole.customer)
    category = _create_category(db)
    now = datetime.now()

    for _ in range(3):
        product = _create_product(db, category.id)
        _create_order(
            db, customer.id, status=OrderStatus.delivered, total_amount="100000", created_at=now,
            items=[(product, 1)],
        )

    response = client.get("/api/v1/admin/dashboard/top-products", params={"limit": 2}, headers=admin_headers)
    assert response.status_code == 200, response.text
    assert len(response.json()["data"]) == 2


# ---- Cache (Redis, TTL 5 phút) ----


def test_summary_is_cached_stale_within_ttl(client: TestClient, db: Session, redis_client) -> None:
    """Gọi lần 1 -> tạo thêm đơn hàng mới trực tiếp trong DB (không qua
    endpoint, không invalidate cache) -> gọi lần 2 NGAY (còn trong TTL) phải
    trả về CÙNG kết quả cũ (cache hit, KHÔNG tính lại) - đây là cách kiểm
    chứng cache đang hoạt động THẬT (đáng tin hơn so sánh thời gian phản hồi
    qua TestClient, vốn có overhead riêng gây nhiễu)."""
    admin_headers = _admin_headers(db)
    customer = _create_user(db, role=UserRole.customer)
    now = datetime.now()
    _create_order(db, customer.id, status=OrderStatus.delivered, total_amount="100000", created_at=now)

    first = client.get("/api/v1/admin/dashboard/summary", headers=admin_headers)
    assert first.status_code == 200, first.text
    assert Decimal(str(first.json()["data"]["total_revenue"])) == Decimal("100000")

    # Thêm đơn MỚI sau khi đã cache - lần gọi kế tiếp KHÔNG được thấy đơn này
    # nếu cache đang hoạt động đúng (TTL 5 phút, chưa hết hạn).
    _create_order(db, customer.id, status=OrderStatus.delivered, total_amount="500000", created_at=now)

    second = client.get("/api/v1/admin/dashboard/summary", headers=admin_headers)
    assert second.status_code == 200, second.text
    assert Decimal(str(second.json()["data"]["total_revenue"])) == Decimal("100000")  # vẫn giá trị CŨ - cache hit
