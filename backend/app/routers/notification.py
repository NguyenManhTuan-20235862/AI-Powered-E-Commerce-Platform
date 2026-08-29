"""Router: Notification / Realtime Module (SSE).

Khung endpoint theo docs/API_SPEC.md - mục 9. `/orders/stream` (task 5.2.1)
đã có logic thật - `/admin/stream` (đơn hàng mới/thống kê Admin) vẫn
placeholder, để dành task khác (ngoài phạm vi 5.2.1).

`/orders/stream` (task 5.2.1) - xác thực qua JWT ở QUERY PARAM (`?token=...`),
KHÔNG PHẢI Authorization header như REST - `EventSource` (Web API chuẩn cho
SSE) không cho set custom header, CÙNG lý do WebSocket (task 5.1.1). ĐƠN GIẢN
HƠN WebSocket: lỗi auth raise thẳng `HTTPException(401/403)` bình thường
(xảy ra ở tầng dependency, TRƯỚC khi `StreamingResponse` được tạo) - không
cần class exception riêng như `WebSocketException`, response 401/403 vẫn là
JSON đọc được qua Network tab lúc debug. Dùng LẠI đúng
`get_token_payload`/`get_current_user` (app/core/security.py), KHÔNG viết
lại decode/blacklist - cùng cách bọc `asyncio.to_thread(...)` cho lệnh Redis/
MySQL sync khi gọi từ handler async này (xem app/core/database.py).

Cơ chế Redis Pub/Sub cross-worker: xem docstring
app/services/notification_service.py.
"""

import asyncio
import json
import logging
from typing import Annotated

import redis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db, get_redis
from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user, get_token_payload, require_role
from app.models.user import User, UserRole
from app.services.notification_service import order_updates_channel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notification"])

# redis-py get_message(timeout=...) - độ trễ TỐI ĐA giữa 2 lần check
# request.is_disconnected() khi không có sự kiện mới (get_message tự block ở
# tầng socket trong khoảng này, KHÔNG phải poll bận tốn CPU) - 3s đủ nhanh để
# dọn sạch subscription Redis sớm sau khi client ngắt kết nối, vẫn đủ dài để
# không tạo quá nhiều round-trip threadpool cho 1 kết nối SSE mở hàng giờ.
_POLL_TIMEOUT_SECONDS = 3.0


def _decode_and_load_user(token: str, db: Session, redis_client: redis.Redis) -> User:
    """Chạy trong `asyncio.to_thread` - gọi LẠI đúng logic decode JWT + check
    blacklist Redis + load User MySQL đã có, KHÔNG viết lại (cùng hàm dùng ở
    app/routers/ai_chat.py:authenticate_websocket)."""
    payload = get_token_payload(token)
    return get_current_user(payload, db, redis_client)


async def authenticate_sse(
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    token: Annotated[str | None, Query(description="Access token JWT, VD: ?token=<access_token>")] = None,
) -> User:
    """Dependency xác thực SSE (task 5.2.1) - raise `HTTPException` bình
    thường (401 thiếu/sai/hết hạn/blacklist token, 403 đúng token nhưng không
    phải Customer) - FastAPI trả lỗi này TRƯỚC KHI endpoint bắt đầu stream,
    đúng như 1 REST endpoint thường."""
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Thiếu token xác thực")

    try:
        user = await asyncio.to_thread(_decode_and_load_user, token, db, redis_client)
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token không hợp lệ hoặc đã hết hạn")

    if user.role != UserRole.customer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Chỉ Customer được xem stream đơn hàng của chính mình"
        )

    return user


def _format_sse(event: str, data: dict) -> str:
    """1 event SSE chuẩn - "event: <tên>\\ndata: <JSON 1 dòng>\\n\\n" (2 dòng
    mới liên tiếp bắt buộc để đánh dấu hết 1 event, xem chuẩn SSE)."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get(
    "/orders/stream",
    summary="Stream sự kiện cập nhật trạng thái đơn hàng realtime (SSE)",
    responses=auth_responses(forbidden=True),
)
async def stream_order_updates(
    request: Request,
    current_user: Annotated[User, Depends(authenticate_sse)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> StreamingResponse:
    """Stream sự kiện cập nhật trạng thái đơn hàng realtime (SSE). Yêu cầu:
    Customer - CHỈ nhận sự kiện của chính đơn hàng thuộc về user này (channel
    Redis riêng theo user_id, xem `notification_service.order_updates_channel`).

    Event đầu tiên luôn là "connected" (báo subscribe Redis đã sẵn sàng, xem
    docstring vòng lặp bên dưới về race condition PUBLISH/SUBSCRIBE) - sau đó
    "order_status" mỗi khi có cập nhật thật từ `PUT /orders/{id}/status`.
    """
    channel = order_updates_channel(current_user.id)

    async def event_generator():
        pubsub = redis_client.pubsub()
        try:
            # SUBSCRIBE trước khi yield "connected" - giảm tối đa (không loại
            # bỏ hoàn toàn được, Pub/Sub không có replay) khoảng hở giữa lúc
            # client coi là "đã kết nối" và lúc THẬT SỰ bắt đầu nhận được
            # event PUBLISH sau đó.
            await asyncio.to_thread(pubsub.subscribe, channel)
            yield _format_sse("connected", {"user_id": current_user.id})

            while True:
                if await request.is_disconnected():
                    break

                message = await asyncio.to_thread(
                    pubsub.get_message,
                    ignore_subscribe_messages=True,
                    timeout=_POLL_TIMEOUT_SECONDS,
                )
                if message is None:
                    continue

                data = json.loads(message["data"])
                yield _format_sse("order_status", data)
        finally:
            # Luôn dọn sạch dù thoát vòng lặp bằng cách nào (disconnect, lỗi
            # bất ngờ...) - KHÔNG rò rỉ subscription/connection Redis.
            try:
                await asyncio.to_thread(pubsub.unsubscribe, channel)
                await asyncio.to_thread(pubsub.close)
            except Exception:
                logger.exception("Lỗi lúc dọn Redis pubsub cho channel %s", channel)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get(
    "/admin/stream",
    summary="Stream sự kiện đơn hàng mới, thống kê realtime cho Admin (SSE)",
    responses=auth_responses(forbidden=True),
)
def stream_admin_events(current_user: Annotated[User, Depends(require_role(UserRole.admin))]) -> None:
    """Stream sự kiện đơn hàng mới, thống kê realtime cho Admin (SSE). Yêu cầu: Admin.

    TODO: implement thật ở task riêng (ngoài phạm vi 5.2.1).
    """
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 9.x")
