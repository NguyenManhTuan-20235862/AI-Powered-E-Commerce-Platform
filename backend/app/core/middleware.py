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


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Set request_id (contextvar) cho cả request, log lại kết quả sau khi xong.

    Áp dụng cho request THÀNH CÔNG lẫn LỖI - log dòng "kết quả" luôn chạy vì đặt
    ở nhánh else (chỉ khi call_next không raise) và finally reset contextvar;
    trường hợp raise (hiếm khi xảy ra vì app đã có catch-all Exception handler ở
    app/main.py nên call_next gần như luôn trả về Response, không raise) vẫn được
    log lại trước khi truyền lỗi tiếp lên, không để lọt request nào không log.

    LƯU Ý: BaseHTTPMiddleware chỉ chạy trên ASGI scope "http" - KHÔNG áp dụng cho
    WebSocket (/ws/chat) và không đo được đúng "thời gian phục vụ" cho SSE
    (/notifications/*/stream) vì call_next() trả về ngay khi bắt đầu stream, chưa
    phải lúc client đóng kết nối. Xem giải thích chi tiết trong summary trả lời
    task 1.4.2.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_var.set(request_id)
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
