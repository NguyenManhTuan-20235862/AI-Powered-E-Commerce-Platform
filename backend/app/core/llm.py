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

import asyncio
from collections.abc import AsyncIterator

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from app.core.config import get_settings

settings = get_settings()

# Giây - timeout CHỈ áp dụng cho TOKEN ĐẦU TIÊN (task 6.1.2, quyết định đã
# chốt) - Ollama local có thể chậm lúc "cold start" (load model vào RAM/VRAM
# lần đầu) nhưng MỘT KHI đã bắt đầu sinh token thì hiếm khi treo giữa chừng -
# KHÔNG đặt timeout cho CẢ stream (câu trả lời dài hợp lệ có thể mất nhiều
# giây hơn) - `LLM_MAX_TOKENS` (config.py) đã là phanh an toàn cho độ dài,
# không cần thêm giới hạn thời gian tổng.
FIRST_TOKEN_TIMEOUT_SECONDS = 12


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


async def astream_llm(messages: list[BaseMessage]) -> AsyncIterator[str]:
    """Stream phản hồi LLM theo từng chunk text (task 6.1.2) - nhận sẵn danh
    sách `BaseMessage` (system/human/ai đã ghép - xem
    `app/services/chat_service.py`, hàm này KHÔNG biết gì về "hội thoại"/
    "lịch sử phiên", chỉ lo phần hạ tầng LLM thuần túy).

    Dùng `.astream()` - async THẬT của langchain-openai (qua `AsyncOpenAI`
    client bên dưới), KHÔNG PHẢI `asyncio.to_thread` bọc quanh `.stream()`
    đồng bộ - khác hẳn cách xử lý PyMongo/redis-py (sync thuần, bắt buộc
    to_thread, xem app/core/database.py) ở nơi khác trong dự án: `ChatOpenAI`
    CÓ hỗ trợ async native, bọc to_thread ở đây sẽ vô nghĩa (phải đợi TOÀN BỘ
    generator chạy xong trong thread rồi mới trả về, phá hỏng đúng mục đích
    stream từng token về client ngay khi có).

    Raise `LLMUnavailableError` nếu: (1) không nhận được token đầu tiên
    trong `FIRST_TOKEN_TIMEOUT_SECONDS` giây (coi như treo - quyết định task
    6.1.2, KHÔNG để user chờ màn hình trống mãi), hoặc (2) lỗi kết nối/
    provider bất kỳ lúc nào trong quá trình stream.
    """
    stream = llm_client.astream(messages)
    try:
        first_chunk = await asyncio.wait_for(stream.__anext__(), timeout=FIRST_TOKEN_TIMEOUT_SECONDS)
    except TimeoutError as exc:
        raise LLMUnavailableError("LLM không phản hồi trong thời gian cho phép - có thể đang quá tải") from exc
    except StopAsyncIteration:
        return
    except Exception as exc:  # noqa: BLE001 - xem giải thích ở ask_llm()
        raise LLMUnavailableError(f"Không thể kết nối tới LLM: {exc}") from exc

    if first_chunk.content:
        yield str(first_chunk.content)

    try:
        async for chunk in stream:
            if chunk.content:
                yield str(chunk.content)
    except Exception as exc:  # noqa: BLE001
        raise LLMUnavailableError(f"Lỗi khi nhận phản hồi từ LLM: {exc}") from exc
