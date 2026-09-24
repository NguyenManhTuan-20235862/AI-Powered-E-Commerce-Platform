"""Cấu hình ứng dụng, đọc từ biến môi trường (.env) bằng Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Hằng số (KHÔNG đọc từ .env - không phải giá trị cấu hình theo môi trường,
# đổi giá trị này là breaking change API) - đặt ở đây (không phải trong
# app/main.py, nơi dùng chính) vì app/core/storage.py (task 3.4.1, URL public
# phục vụ ảnh upload) CŨNG cần đúng giá trị này để khớp `location /api/` bên
# nginx.conf sau này - main.py IMPORT lại từ đây thay vì tự định nghĩa,
# tránh 2 nơi hardcode "/api/v1" độc lập dễ lệch nhau nếu 1 trong 2 đổi.
API_PREFIX = "/api/v1"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "AI-Powered E-Commerce Platform API"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # MySQL (SQLAlchemy) - dùng cho Auth, Product, Order, Cart
    DATABASE_URL: str

    # MongoDB - dùng cho Chat log, Review
    MONGO_URI: str
    MONGO_DB_NAME: str = "ecommerce_mongo"

    # Redis - cache, session, rate limit...
    REDIS_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Agent (LangChain) - task 6.1.1: cấu hình LINH HOẠT đổi provider
    # (Ollama local, miễn phí, dùng cho dev <-> OpenAI thật, trả phí, dùng cho
    # demo/production) CHỈ qua biến môi trường, KHÔNG sửa code -
    # `ChatOpenAI` (langchain-openai, app/core/llm.py) hoạt động với BẤT KỲ
    # endpoint tương thích OpenAI nào (chỉ cần đổi base_url + api_key), không
    # cần cài thư viện riêng cho Ollama. Thay thế field `OPENAI_API_KEY` cũ
    # (khai báo từ trước nhưng chưa có code nào dùng) - field đó chỉ hoạt
    # động đúng 1 provider (OpenAI thật), không đủ linh hoạt cho yêu cầu này.
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "llama3.2"
    # Giới hạn chi phí/độ dài response - đặt sẵn dù Ollama miễn phí (không
    # tính theo token) để khi đổi sang OpenAI thật (demo/production) đã có
    # sẵn giới hạn, không quên bảo vệ chi phí lúc đổi provider.
    LLM_MAX_TOKENS: int = 1000
    # Giây - tránh treo request khi LLM chậm/không phản hồi (cùng tinh thần
    # timeout 3s đã đặt cho Mongo/Redis ở database.py, nhưng LLM cần ngưỡng
    # dài hơn hẳn - sinh văn bản chậm hơn nhiều so với 1 query DB).
    LLM_TIMEOUT: int = 30

    # Scheduler (task 3.5.2) - lịch chạy job đồng bộ Product -> MongoDB
    # (backend/scripts/run_scheduler.py), cú pháp cron chuẩn (phút giờ ngày
    # tháng thứ), giờ Việt Nam (Asia/Ho_Chi_Minh). Mặc định 2h sáng hàng
    # ngày - giờ ít traffic nhất. Đọc qua biến môi trường để TEST được lịch
    # chạy gần (VD "*/2 * * * *" - mỗi 2 phút) mà KHÔNG cần sửa code.
    PRODUCT_SYNC_CRON: str = "0 2 * * *"

    # Payment - VNPay sandbox thật (task "Quyết định và hoàn thiện thanh
    # toán") - KHÔNG có giá trị mặc định hợp lệ cho TMN_CODE/HASH_SECRET (rỗng
    # = chưa cấu hình, `payment_service.build_payment_url()` tự raise lỗi rõ
    # ràng thay vì ký request với secret rỗng/sai). Đăng ký tài khoản sandbox
    # tại https://sandbox.vnpayment.vn để lấy 2 giá trị này.
    VNPAY_TMN_CODE: str = ""
    VNPAY_HASH_SECRET: str = ""
    # URL cổng thanh toán sandbox VNPay (v2.1.0) - CÓ THỂ giữ nguyên, đổi khi
    # VNPay cập nhật version API hoặc chuyển sang endpoint production thật.
    VNPAY_PAY_URL: str = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    # URL BACKEND đầy đủ (KHÔNG PHẢI tên service Docker - đây là `vnp_ReturnUrl`
    # gửi cho VNPay, trình duyệt CỦA KHÁCH sẽ điều hướng thẳng tới URL này sau
    # khi thanh toán xong, cùng nguyên tắc NEXT_PUBLIC_API_URL - phải là URL
    # trình duyệt gọi được) - trỏ đúng `GET /payments/callback`.
    VNPAY_RETURN_URL: str = "http://localhost:8000/api/v1/payments/callback"
    # URL gốc FRONTEND (KHÁC mọi biến URL khác trong file này - đây là nơi DUY
    # NHẤT Backend cần biết địa chỉ Frontend) - dùng để Backend tự điều hướng
    # trình duyệt khách VỀ LẠI trang kết quả thanh toán
    # (`/checkout/payment-result`) sau khi xử lý xong `GET /payments/callback`.
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    @property
    def is_production(self) -> bool:
        """True khi APP_ENV=production - dùng để ẩn Swagger/ReDoc docs."""
        return self.APP_ENV.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    """Trả về instance Settings dùng chung (cache để không đọc lại .env nhiều lần)."""
    return Settings()
