"""Middleware gắn request_id + log method/path/status/thời gian xử lý cho MỌI
request HTTP (task 1.4.2 - item 3).
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import request_id_var

logger = logging.getLogger(__name__)

# Path SSE (task 5.2.1, đóng KNOWN_TODOS #3) - call_next() trả về StreamingResponse
# NGAY khi bắt đầu stream (ngay sau khi qua auth), KHÔNG đợi tới lúc client đóng
# kết nối (có thể mở hàng giờ) - duration_ms đo theo cách của middleware này vì
# vậy vô nghĩa cho path dạng này (luôn ra số gần 0, không phản ánh "thời gian
# phục vụ" thật). Loại các path này khỏi đo/log duration NGAY TỪ ĐẦU dispatch()
# thay vì viết lại middleware bằng raw ASGI (không tương xứng công sức cho 1 vấn
# đề chỉ ảnh hưởng độ chính xác log, không phải chức năng) - vẫn giữ request_id
# cho path này để log ở nơi khác (nếu có) vẫn có request_id đúng.
_SSE_PATH_PREFIXES = ("/api/v1/notifications/",)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Set request_id (contextvar) cho cả request, log lại kết quả sau khi xong.

    Áp dụng cho request THÀNH CÔNG lẫn LỖI - log dòng "kết quả" luôn chạy vì đặt
    ở nhánh else (chỉ khi call_next không raise) và finally reset contextvar;
    trường hợp raise (hiếm khi xảy ra vì app đã có catch-all Exception handler ở
    app/main.py nên call_next gần như luôn trả về Response, không raise) vẫn được
    log lại trước khi truyền lỗi tiếp lên, không để lọt request nào không log.

    LƯU Ý: BaseHTTPMiddleware chỉ chạy trên ASGI scope "http" - KHÔNG áp dụng cho
    WebSocket (/ws/chat). Path SSE (`_SSE_PATH_PREFIXES`) được xử lý riêng, xem
    nhánh đầu `dispatch()` bên dưới.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_var.set(request_id)

        if request.url.path.startswith(_SSE_PATH_PREFIXES):
            try:
                response = await call_next(request)
                response.headers["X-Request-ID"] = request_id
                return response
            finally:
                request_id_var.reset(token)

        start = time.perf_counter()
        try:
            try:
                response = await call_next(request)
            except Exception:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.exception(
                    "%s %s -> lỗi chưa xử lý (%.1fms)",
                    request.method,
                    request.url.path,
                    duration_ms,
                )
                raise
            else:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "%s %s -> %d (%.1fms)",
                    request.method,
                    request.url.path,
                    response.status_code,
                    duration_ms,
                )
                response.headers["X-Request-ID"] = request_id
                return response
        finally:
            # Reset SAU khi đã log xong (kể cả 2 nhánh trên) - nếu reset trước,
            # dòng log request thành công (chạy sau finally) sẽ đọc lại giá trị
            # mặc định "-" thay vì request_id thật, làm mất tác dụng của middleware.
            request_id_var.reset(token)
