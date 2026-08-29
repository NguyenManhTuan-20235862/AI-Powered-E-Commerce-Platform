"""Test SSE /notifications/orders/stream (task 5.2.1) - Redis Pub/Sub THẬT
(không mock, cùng triết lý MySQL/Redis thật xuyên suốt dự án, xem
tests/conftest.py).

Phần xác thực (401/403) test qua HTTP thật (`client.get()` bình thường,
KHÔNG streaming - request thất bại trước khi StreamingResponse được tạo,
xem authenticate_sse trong app/routers/notification.py) - cùng tinh thần
test_ai_chat_websocket.py (task 5.1.1), đơn giản hơn WS vì không cần bắt
exception đặc biệt.

Phần đọc sự kiện SSE THẬT (subscribe/publish/nhận/dọn dẹp) KHÔNG đi qua HTTP/
`TestClient`/`httpx.ASGITransport` - đã tự kiểm chứng: cả `TestClient.stream()`
(sync) LẪN `httpx.AsyncClient` + `ASGITransport` (async) đều KHÔNG đọc được
tăng dần từ 1 `StreamingResponse` không bao giờ tự kết thúc (SSE endpoint
đúng nghĩa - vòng lặp vô hạn chờ sự kiện tiếp theo) - cả 2 cách đều "treo"
chờ generator CHẠY XONG HẲN trước khi trả về BẤT KỲ dữ liệu nào cho client,
dù server xử lý đúng 100% (đã xác nhận bằng `curl` thật vào backend đang
chạy: nhận "connected" ngay lập tức, xem tail bash history). Đây là giới hạn
tầng test (`ASGITransport` buffer toàn bộ response trước khi trả, không phải
lỗi code) - giải pháp: gọi TRỰC TIẾP `notification.stream_order_updates()`
như 1 hàm Python async thường (bỏ qua tầng HTTP/ASGI - phần đó là trách
nhiệm của Starlette, không phải logic cần test ở đây), tự `await
response.body_iterator.__anext__()` để lấy từng event, tự gọi
`body_iterator.aclose()` để mô phỏng CHÍNH XÁC hành vi Starlette làm khi
client ngắt kết nối thật (dọn dẹp qua đúng nhánh `finally` trong generator).
"""

import asyncio
import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.models.category import Category
from app.models.product import Product
from app.models.user import User, UserRole
from app.routers import notification

VALID_CHECKOUT_PAYLOAD = {
    "shipping_name": "Nguyễn Văn A",
    "shipping_address": "123 Đường ABC, Q1, TP.HCM",
    "shipping_phone": "0900000000",
}


class _AlwaysConnectedRequest:
    """Stub thay `fastapi.Request` - CHỈ cần `is_disconnected()` khi gọi
    `stream_order_updates()` trực tiếp (bỏ qua tầng HTTP thật, xem docstring
    module). Luôn trả `False` - test tự kiểm soát điểm dừng bằng cách đọc
    đúng số event cần rồi gọi `aclose()` thủ công (mô phỏng disconnect thật),
    KHÔNG dựa vào cờ này để dừng vòng lặp.
    """

    async def is_disconnected(self) -> bool:
        return False


def _parse_sse_chunk(chunk: str) -> tuple[str | None, dict]:
    event = None
    data: dict = {}
    for line in chunk.split("\n"):
        if line.startswith("event:"):
            event = line[len("event:") :].strip()
        elif line.startswith("data:"):
            data = json.loads(line[len("data:") :].strip())
    return event, data


def _create_category(db: Session) -> Category:
    category = Category(name="Danh mục", slug=f"cat-sse-{datetime.now().timestamp()}")
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def _create_product(db: Session, category_id: int) -> Product:
    product = Product(
        category_id=category_id,
        name="Sản phẩm test SSE",
        slug=f"sp-sse-{datetime.now().timestamp()}",
        price="100000",
        stock_quantity=10,
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def _create_customer(db: Session) -> User:
    user = User(
        email=f"sse-customer-{datetime.now().timestamp()}@example.com",
        password_hash=hash_password("password123"),
        full_name="SSE Customer Test",
        role=UserRole.customer,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_admin(db: Session) -> User:
    user = User(
        email=f"sse-admin-{datetime.now().timestamp()}@example.com",
        password_hash=hash_password("password123"),
        full_name="SSE Admin Test",
        role=UserRole.admin,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _headers_for(user: User) -> dict:
    token = create_access_token(user_id=user.id, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def _expired_customer_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": "customer",
        "type": "access",
        "iat": now - timedelta(minutes=10),
        "exp": now - timedelta(minutes=5),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _create_order(client: TestClient, db: Session, customer: User) -> int:
    category = _create_category(db)
    product = _create_product(db, category.id)
    headers = _headers_for(customer)
    add_response = client.post("/api/v1/cart/items", json={"product_id": product.id, "quantity": 1}, headers=headers)
    assert add_response.status_code == 201, add_response.text
    order_response = client.post("/api/v1/orders", json=VALID_CHECKOUT_PAYLOAD, headers=headers)
    assert order_response.status_code == 201, order_response.text
    return order_response.json()["data"]["id"]


# ---- Xác thực (qua HTTP thật, KHÔNG streaming - xem docstring module) ----


def test_no_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/notifications/orders/stream")
    assert response.status_code == 401


def test_malformed_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/notifications/orders/stream?token=not-a-real-jwt")
    assert response.status_code == 401


def test_expired_token_returns_401(client: TestClient, db: Session) -> None:
    customer = _create_customer(db)
    token = _expired_customer_token(customer.id)
    response = client.get(f"/api/v1/notifications/orders/stream?token={token}")
    assert response.status_code == 401


def test_blacklisted_token_returns_401(client: TestClient, db: Session) -> None:
    customer = _create_customer(db)
    token = create_access_token(user_id=customer.id, role=customer.role.value)
    logout_response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_response.status_code == 200

    response = client.get(f"/api/v1/notifications/orders/stream?token={token}")
    assert response.status_code == 401


def test_admin_token_returns_403(client: TestClient, db: Session) -> None:
    admin = _create_admin(db)
    token = create_access_token(user_id=admin.id, role=admin.role.value)
    response = client.get(f"/api/v1/notifications/orders/stream?token={token}")
    assert response.status_code == 403


# ---- Redis Pub/Sub thật - gọi trực tiếp generator (task 5.2.1, KHÔNG mock) ----


def test_valid_customer_receives_connected_event(db: Session, redis_client) -> None:
    customer = _create_customer(db)

    async def scenario():
        response = await notification.stream_order_updates(_AlwaysConnectedRequest(), customer, redis_client)
        first_chunk = await response.body_iterator.__anext__()
        await response.body_iterator.aclose()
        return _parse_sse_chunk(first_chunk)

    event, data = asyncio.run(scenario())
    assert event == "connected"
    assert data["user_id"] == customer.id


def test_admin_update_status_publishes_event_received_by_owner(client: TestClient, db: Session, redis_client) -> None:
    customer = _create_customer(db)
    order_id = _create_order(client, db, customer)
    admin = _create_admin(db)

    async def scenario():
        response = await notification.stream_order_updates(_AlwaysConnectedRequest(), customer, redis_client)
        agen = response.body_iterator
        connected_event, _ = _parse_sse_chunk(await agen.__anext__())
        assert connected_event == "connected"

        # SUBSCRIBE đã chắc chắn xong (đã nhận "connected") - giờ mới đổi
        # trạng thái đơn hàng qua HTTP thật (sync, chạy đồng bộ trong hàm
        # async này - không sao, không có việc gì khác cần chạy song song
        # tại thời điểm này).
        status_response = client.put(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "confirmed"},
            headers=_headers_for(admin),
        )
        assert status_response.status_code == 200

        order_event, data = _parse_sse_chunk(await asyncio.wait_for(agen.__anext__(), timeout=5))
        await agen.aclose()
        return order_event, data

    order_event, data = asyncio.run(scenario())
    assert order_event == "order_status"
    assert data["order_id"] == order_id
    assert data["status"] == "confirmed"
    assert "timestamp" in data


def test_other_customer_order_update_not_received(client: TestClient, db: Session, redis_client) -> None:
    """Đúng phân kênh theo user_id - user A KHÔNG nhận được sự kiện đổi trạng
    thái đơn hàng của user B."""
    customer_a = _create_customer(db)
    customer_b = _create_customer(db)
    order_b_id = _create_order(client, db, customer_b)
    admin = _create_admin(db)

    async def scenario():
        response = await notification.stream_order_updates(_AlwaysConnectedRequest(), customer_a, redis_client)
        agen = response.body_iterator
        connected_event, _ = _parse_sse_chunk(await agen.__anext__())
        assert connected_event == "connected"

        status_response = client.put(
            f"/api/v1/orders/{order_b_id}/status",
            json={"status": "confirmed"},
            headers=_headers_for(admin),
        )
        assert status_response.status_code == 200

        # Channel của customer_a không có gì để nhận - PHẢI timeout (KHÔNG
        # được có event nào trong khoảng chờ hợp lý).
        try:
            await asyncio.wait_for(agen.__anext__(), timeout=4)
            received_something = True
        except asyncio.TimeoutError:
            received_something = False
        await agen.aclose()
        return received_something

    received_something = asyncio.run(scenario())
    assert received_something is False


def test_disconnect_cleans_up_redis_subscription(db: Session, redis_client) -> None:
    customer = _create_customer(db)
    channel = f"order_updates:{customer.id}"

    async def scenario():
        response = await notification.stream_order_updates(_AlwaysConnectedRequest(), customer, redis_client)
        agen = response.body_iterator
        connected_event, _ = _parse_sse_chunk(await agen.__anext__())
        assert connected_event == "connected"
        # Subscribe THẬT đã có trước khi kiểm tra dọn sạch sau đó.
        assert redis_client.pubsub_numsub(channel)[0][1] == 1

        # aclose() - ĐÚNG những gì Starlette tự làm với body_iterator khi
        # client ngắt kết nối thật (chạy nhánh `finally` trong generator,
        # unsubscribe + close pubsub) - test TRỰC TIẾP hành vi dọn dẹp, không
        # cần giả lập disconnect qua tầng HTTP.
        await agen.aclose()

    asyncio.run(scenario())
    assert redis_client.pubsub_numsub(channel)[0][1] == 0
