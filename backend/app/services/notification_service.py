"""Business logic: Notification / Realtime (task 5.2.1) - Redis Pub/Sub cho
SSE cập nhật trạng thái đơn hàng.

LẦN ĐẦU TIÊN dự án dùng Redis cho pub/sub (trước đó CHỈ cache task 3.3.1,
session/blacklist task 3.3.2) - cần thiết vì Backend chạy Gunicorn NHIỀU
worker ở production (task 2.1.2, `_WORKERS_CAP=4`): Admin đổi trạng thái đơn
có thể được worker A xử lý, trong khi customer đang giữ kết nối SSE ở worker
B - 2 process HOÀN TOÀN riêng biệt (không share memory), CHỈ Redis (hạ tầng
NGOÀI process, dùng chung bởi mọi worker) mới truyền được sự kiện qua worker
khác. Đây không phải trường hợp hiếm - với round-robin qua 4 worker, phần
lớn request rơi vào worker KHÁC với worker đang giữ SSE connection.

Channel RIÊNG từng user (`order_updates:{user_id}`) - KHÔNG dùng 1 channel
chung rồi filter ở client/server: subscribe hết mọi sự kiện rồi lọc sẽ để lộ
việc đơn hàng của user khác đang đổi trạng thái (dù không hiện ra UI, vẫn là
rò rỉ thông tin không cần thiết qua kênh truyền tải).
"""

import json
from datetime import datetime, timezone

import redis

from app.models.order import OrderStatus


def order_updates_channel(user_id: int) -> str:
    """Tên channel Redis Pub/Sub riêng cho 1 user - SSE handler
    (app/routers/notification.py) SUBSCRIBE đúng channel này của
    `current_user.id`, không bao giờ subscribe channel của user khác."""
    return f"order_updates:{user_id}"


def publish_order_status_update(redis_client: redis.Redis, *, user_id: int, order_id: int, new_status: OrderStatus) -> None:
    """PUBLISH sự kiện đổi trạng thái đơn hàng (task 5.2.1) - PHẢI gọi SAU KHI
    `order_service.update_order_status()` đã `db.commit()` thành công (xem
    app/routers/order.py: chỉ gọi hàm này trong nhánh KHÔNG có exception).

    PUBLISH khi không có subscriber nào đang lắng nghe channel (user không mở
    SSE lúc đó) vẫn thành công bình thường (redis-py trả về 0 - số subscriber
    nhận được), KHÔNG lỗi - đúng ngữ nghĩa "fire and forget" của Pub/Sub,
    KHÔNG phải hàng đợi persistent (không tự "gửi lại sau" cho subscriber mở
    kết nối muộn hơn). Chấp nhận được cho tính năng "cập nhật realtime trong
    lúc đang xem" - `GET /orders/{id}` vẫn là nguồn sự thật đầy đủ nếu user bỏ
    lỡ sự kiện (đóng tab, mất mạng...).
    """
    payload = {
        "order_id": order_id,
        "status": new_status.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    redis_client.publish(order_updates_channel(user_id), json.dumps(payload))
