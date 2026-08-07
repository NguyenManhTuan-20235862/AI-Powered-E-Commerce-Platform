"""Entry point của FastAPI app: khởi tạo app, middleware, OpenAPI/Swagger metadata
và include toàn bộ router theo docs/API_SPEC.md.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pymongo.errors import PyMongoError
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import API_PREFIX, get_settings
from app.core.database import mongo_client
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.core.storage import UPLOAD_ROOT, UPLOAD_URL_PREFIX
from app.routers import (
    ai_chat,
    auth,
    cart,
    category,
    dashboard,
    notification,
    order,
    payment,
    product,
    review,
    user,
)
from app.schemas.common import ErrorResponse

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)

# Thứ tự và mô tả tag khớp với thứ tự module trong docs/API_SPEC.md.
TAGS_METADATA = [
    {"name": "Auth", "description": "Đăng ký, đăng nhập, JWT (access token + refresh token)."},
    {"name": "User", "description": "Thông tin cá nhân và quản trị user (Admin)."},
    {"name": "Product", "description": "Catalog sản phẩm: xem, tìm kiếm, quản lý (Admin)."},
    {"name": "Category", "description": "Danh mục sản phẩm."},
    {"name": "Cart", "description": "Giỏ hàng của Customer."},
    {"name": "Order", "description": "Đặt hàng, lịch sử đơn hàng, quản lý đơn hàng (Admin)."},
    {"name": "Payment", "description": "Thanh toán VNPay/Momo sandbox (task 8.1)."},
    {"name": "Review", "description": "Đánh giá sản phẩm, lưu ở MongoDB."},
    {"name": "AI Agent / Chat", "description": "Chat AI qua WebSocket và REST fallback (LangChain)."},
    {"name": "Notification", "description": "Sự kiện realtime qua SSE (task 9.x)."},
    {"name": "Dashboard Admin", "description": "Thống kê tổng quan cho Admin."},
    {"name": "Health Check", "description": "Kiểm tra service sống - dùng cho Docker healthcheck / CI."},
]

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "API cho nền tảng thương mại điện tử tích hợp AI Agent. "
        "Chi tiết đặc tả endpoint: xem `docs/API_SPEC.md`.\n\n"
        "Toàn bộ endpoint (trừ endpoint đánh dấu Public) yêu cầu header "
        "`Authorization: Bearer <access_token>`."
    ),
    version="0.1.0",
    # Ẩn Swagger/ReDoc khi chạy production - tránh lộ cấu trúc API ra ngoài.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
    openapi_tags=TAGS_METADATA,
)

# TODO: giới hạn allow_origins về domain thật của frontend trước khi lên production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# BaseHTTPMiddleware chỉ áp dụng cho scope "http" - KHÔNG chạy trên WebSocket
# (/ws/chat), và không đo đúng thời gian phục vụ cho SSE (xem docstring trong
# app/core/middleware.py).
app.add_middleware(RequestContextMiddleware)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Bọc mọi HTTPException (401/403/404/429/501...) vào đúng envelope
    `{ success, data, message }` theo docs/API_SPEC.md - mặc định FastAPI trả
    `{"detail": ...}`, không khớp định dạng đã công bố. Router chỉ cần
    `raise HTTPException(status_code=..., detail=...)` như bình thường, không
    cần tự tạo ErrorResponse thủ công.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(message=str(exc.detail)).model_dump(),
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """422 - Pydantic validate request (body/query/path) sai. Liệt kê rõ field
    nào sai trong `message` để Frontend hiển thị lỗi form đúng chỗ.

    CHỈ log tên field + lý do lỗi (`loc`, `msg`) - KHÔNG log `exc.body` (giá trị
    gốc client gửi lên): field lỗi có thể chính là password/token (VD: đăng ký
    với password quá ngắn), log nguyên body sẽ vô tình ghi plaintext bí mật vào
    file log.
    """
    field_errors = [
        {
            "field": ".".join(str(part) for part in err["loc"] if part not in ("body", "query", "path")),
            "message": err["msg"],
        }
        for err in exc.errors()
    ]
    message = "; ".join(f"{e['field']}: {e['message']}" for e in field_errors) or "Dữ liệu gửi lên không hợp lệ"

    logger.warning("Validation error tại %s %s: %s", request.method, request.url.path, field_errors)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ErrorResponse(message=message, error_code="VALIDATION_ERROR").model_dump(),
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """500 - lỗi DB (mất kết nối, constraint violation, deadlock do race
    condition...). Log traceback đầy đủ để debug, response ra ngoài CHUNG CHUNG -
    không lộ connection string/tên bảng/cột hay câu SQL thật cho client.
    """
    logger.error(
        "Lỗi database tại %s %s: %s", request.method, request.url.path, exc.__class__.__name__, exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(message="Lỗi hệ thống, vui lòng thử lại sau", error_code="DATABASE_ERROR").model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """500 - bắt mọi lỗi chưa lường trước. Đặt SAU CÙNG trong file để dễ đọc theo
    thứ tự "cụ thể -> chung chung", dù thực tế Starlette tự chọn handler khớp
    nhất theo MRO của exception (không phụ thuộc thứ tự @app.exception_handler
    được gọi) - handler cụ thể hơn ở trên (HTTPException, RequestValidationError,
    SQLAlchemyError) luôn được ưu tiên trước handler này với đúng loại lỗi tương ứng.
    """
    logger.error(
        "Lỗi chưa xử lý tại %s %s: %s", request.method, request.url.path, exc.__class__.__name__, exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(message="Lỗi hệ thống, vui lòng thử lại sau", error_code="INTERNAL_ERROR").model_dump(),
    )


# Upload ảnh sản phẩm (task 3.4.1) - lưu local, serve qua StaticFiles. Tạo
# thư mục trước khi mount (StaticFiles lỗi ngay lúc khởi động app nếu thư mục
# chưa tồn tại) - xem app/core/storage.py cho lý do chọn giải pháp local này.
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
app.mount(UPLOAD_URL_PREFIX, StaticFiles(directory=UPLOAD_ROOT), name="uploads")

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(user.router, prefix=API_PREFIX)
app.include_router(product.router, prefix=API_PREFIX)
app.include_router(category.router, prefix=API_PREFIX)
app.include_router(cart.router, prefix=API_PREFIX)
app.include_router(order.router, prefix=API_PREFIX)
app.include_router(payment.router, prefix=API_PREFIX)
app.include_router(review.router, prefix=API_PREFIX)
app.include_router(ai_chat.router, prefix=API_PREFIX)
app.include_router(notification.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)


@app.get("/", include_in_schema=False)
def root() -> dict[str, str]:
    return {"message": "Hello World"}


@app.get("/health", tags=["Health Check"], summary="Kiểm tra service sống")
def health() -> dict[str, str]:
    """Health check endpoint - dùng cho Docker healthcheck / load balancer / CI.

    `status` (task 2.x, giữ nguyên) LUÔN "ok" nếu process FastAPI còn sống -
    KHÔNG đổi theo kết quả ping MongoDB bên dưới, dù có thêm field `mongodb`
    (task 3.2.3) báo trạng thái kết nối thật. Cố tình tách 2 khái niệm này:
    Docker healthcheck (`docker-compose.yml`) chỉ dựa vào HTTP status code
    (200 hay không) của response này để quyết định service "healthy" - nếu để
    `status`/status code đổi theo MongoDB, 1 lần Mongo chập chờn sẽ khiến
    Docker đánh dấu Backend "unhealthy" toàn bộ, kéo theo chặn Frontend khởi
    động (`depends_on: backend: condition: service_healthy`) - dù hiện tại
    KHÔNG có tính năng thật nào (auth/product/cart/order, đều dùng MySQL) phụ
    thuộc MongoDB. `mongodb` chỉ mang tính THÔNG TIN cho người/monitoring đọc
    thêm, không làm đổi hành vi healthcheck.
    """
    try:
        mongo_client.admin.command("ping")
        mongo_status = "ok"
    except PyMongoError:
        mongo_status = "unreachable"

    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "mongodb": mongo_status,
    }
