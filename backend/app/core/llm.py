"""LLM client cho AI Agent (task 6.1.1) - khởi tạo `ChatOpenAI`
(langchain-openai), cấu hình LINH HOẠT đổi provider (Ollama local, miễn phí,
dùng cho dev <-> OpenAI thật, trả phí, dùng cho demo/production) CHỈ qua biến
môi trường `LLM_*` (app/core/config.py), KHÔNG sửa code - `ChatOpenAI` hoạt
động với BẤT KỲ endpoint tương thích OpenAI nào (chỉ cần đổi `base_url` +
`api_key`), Ollama tự expose sẵn API tương thích OpenAI tại `/v1` nên không
cần cài thư viện riêng cho Ollama.

Quyết định quan trọng: khởi tạo `llm_client` ở MODULE-LEVEL, cùng nguyên tắc
`mongo_client`/`redis_client` trong `app/core/database.py` - constructor của
`ChatOpenAI` CHỈ lưu lại config (base_url/api_key/model...), KHÔNG tự mở kết
nối mạng nào ngay lúc khởi tạo (lazy, giống PyMongo/redis-py) - app khởi động
BÌNH THƯỜNG kể cả khi LLM_BASE_URL không kết nối được/LLM_API_KEY sai/thiếu.
Lỗi CHỈ lộ ra khi thực sự gọi `ask_llm()` (tức là lúc gọi `.invoke()` thật) -
bọc riêng, raise `LLMUnavailableError` (thông báo rõ ràng) thay vì để lộ
exception gốc của langchain/openai/httpx ra router/WebSocket handler phía
trên (chưa cần biết implementation LLM đang dùng thư viện gì).
"""

from langchain_openai import ChatOpenAI

from app.core.config import get_settings

settings = get_settings()


class LLMUnavailableError(Exception):
    """Raise khi gọi LLM thất bại - không kết nối được (Ollama chưa chạy/sai
    LLM_BASE_URL), timeout (LLM_TIMEOUT), hoặc provider từ chối (API key sai/
    hết hạn mức OpenAI). Router/WebSocket handler (task 6.1.2 trở đi) bắt lỗi
    này để trả thông báo rõ ràng cho user - KHÔNG để crash toàn bộ request/
    connection, các tính năng khác của app vẫn hoạt động bình thường khi LLM
    chưa sẵn sàng (đúng quyết định đã chốt cho task 6.1.1)."""


# api_key: Ollama KHÔNG check giá trị này nhưng `ChatOpenAI`/openai SDK bắt
# buộc phải có 1 giá trị non-empty - "not-set" chỉ dùng khi LLM_API_KEY rỗng
# hoàn toàn (VD quên set .env) để KHÔNG crash lúc khởi tạo, lỗi thật (nếu
# provider yêu cầu key hợp lệ, VD OpenAI) sẽ lộ ra đúng lúc gọi ask_llm().
# base_url: rỗng ("") -> None, để ChatOpenAI tự dùng endpoint OpenAI mặc định
# (KHÔNG truyền thẳng chuỗi rỗng - sẽ khiến client cố gọi tới URL rỗng thay
# vì fallback đúng default).
llm_client = ChatOpenAI(
    base_url=settings.LLM_BASE_URL or None,
    api_key=settings.LLM_API_KEY or "not-set",
    model=settings.LLM_MODEL,
    max_tokens=settings.LLM_MAX_TOKENS,
    timeout=settings.LLM_TIMEOUT,
)


def ask_llm(message: str) -> str:
    """Gửi 1 tin nhắn (user turn đơn) tới LLM, trả về nội dung phản hồi dạng
    text. Raise `LLMUnavailableError` nếu gọi thất bại - xem docstring class
    ở trên."""
    try:
        response = llm_client.invoke(message)
    except Exception as exc:  # noqa: BLE001 - cố tình bắt rộng: che TOÀN BỘ
        # loại lỗi có thể từ langchain/openai/httpx (ConnectError, Timeout,
        # APIStatusError...) thành 1 loại lỗi DUY NHẤT phía trên cần biết -
        # router/WebSocket handler không cần (và không nên) phân biệt từng
        # loại exception gốc của 1 thư viện ngoài.
        raise LLMUnavailableError(f"Không thể kết nối tới LLM: {exc}") from exc
    return str(response.content)
