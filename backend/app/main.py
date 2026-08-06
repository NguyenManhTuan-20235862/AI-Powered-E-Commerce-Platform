"""Entry point của FastAPI app: khởi tạo app, middleware, OpenAPI/Swagger metadata
và include toàn bộ router theo docs/API_SPEC.md.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
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

settings = get_settings()

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

API_PREFIX = "/api/v1"
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
    """Health check endpoint - dùng cho Docker healthcheck / load balancer / CI."""
    return {"status": "ok", "app": settings.APP_NAME, "env": settings.APP_ENV}
