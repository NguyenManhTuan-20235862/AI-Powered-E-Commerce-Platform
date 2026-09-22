"""Business logic: AI Chat (task 5.1.1, agent thật task 6.1.2) - lưu tin nhắn
vào MongoDB `chat_logs`, ghép ngữ cảnh hội thoại (system prompt + lịch sử
phiên đã cắt bớt) và stream phản hồi qua `app/core/llm.py`.

Hàm ĐỌC/GHI Mongo ở đây SYNC (pymongo, quyết định task 3.2.3, xem
app/core/database.py) - nơi gọi (WebSocket handler async trong
app/routers/ai_chat.py) PHẢI tự bọc `asyncio.to_thread(...)`, KHÔNG tự làm ở
đây - giữ phần Mongo của service layer thuần sync, đúng convention 100% sync
hiện tại của mọi service khác (cart_service.py, order_service.py...).
`stream_agent_reply()` là NGOẠI LỆ có chủ đích - hàm `async def` (gọi
`astream_llm()` async thật, xem giải thích ở app/core/llm.py) nhưng vẫn tự
bọc `asyncio.to_thread()` cho riêng phần đọc Mongo bên trong nó.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from pymongo.database import Database as MongoDatabase

from app.core.llm import astream_llm
from app.schemas.chat_log import ChatLogCreate

CHAT_LOGS_COLLECTION = "chat_logs"

# Giữ tối đa 20 tin nhắn GẦN NHẤT (10 lượt hỏi-đáp) làm ngữ cảnh gửi cho LLM
# (task 6.1.2, quyết định "nhớ nhiều nhất có thể trong giới hạn an toàn",
# KHÔNG PHẢI gửi mù toàn bộ lịch sử dù dài bao nhiêu) - đếm theo SỐ TIN NHẮN,
# KHÔNG ước tính token: model thật đang chạy (Llama qua Ollama) có tokenizer
# khác hẳn `tiktoken` (chỉ đúng cho model OpenAI) - ước tính token ở đây sẽ
# SAI, đếm theo tin nhắn không phụ thuộc model nào, đủ an toàn cho quy mô hội
# thoại tư vấn mua sắm thực tế (không phải hội thoại hàng trăm lượt).
MAX_HISTORY_MESSAGES = 20

# Tiếng Việt, ngắn gọn - CHƯA có tool query DB thật (task 6.2/6.3), nên PHẢI
# tự giới hạn phạm vi trả lời: không bịa giá/tồn kho sản phẩm cụ thể, gợi ý
# xem catalog thay vì đoán mò - tránh AI "ảo giác" thông tin sai lệch về sản
# phẩm thật đang bán.
SYSTEM_PROMPT = (
    "Bạn là trợ lý mua sắm thân thiện của Vun - nền tảng thương mại điện tử "
    "Việt Nam. Trả lời ngắn gọn, tự nhiên, luôn bằng tiếng Việt. Bạn CHƯA có "
    "quyền truy cập dữ liệu sản phẩm/giá/tồn kho thật - nếu khách hỏi về sản "
    "phẩm cụ thể, giá cả, hoặc tình trạng còn hàng, hãy trả lời chung chung "
    "và gợi ý khách xem trực tiếp trang danh mục sản phẩm để có thông tin "
    "chính xác nhất, KHÔNG bịa ra thông tin sản phẩm/giá cụ thể nào."
)


def new_session_id() -> str:
    """Sinh session_id mới cho 1 kết nối WebSocket (task 5.1.1).

    UUID4, KHÔNG liên quan ObjectId Mongo - chỉ là chuỗi định danh để gom
    nhóm tin nhắn cùng 1 phiên (xem docstring app/schemas/chat_log.py).
    Sinh MỖI LẦN connect, KHÔNG hỗ trợ client gửi lại session_id cũ để resume
    (quyết định đơn giản hoá cho task này - để dành task 6.x nếu AI Agent
    thật cần ngữ cảnh hội thoại liên tục qua nhiều lần connect).
    """
    return str(uuid.uuid4())


def save_chat_log(mongo_db: MongoDatabase, log: ChatLogCreate) -> None:
    """Insert 1 document vào `chat_logs` (task 3.2.1 - 1 document/1 tin nhắn,
    kể cả tin nhắn user lẫn phản hồi assistant/system đều là 1 document riêng).

    `created_at` set NGAY TRƯỚC KHI insert (không nhận từ input) - đúng
    quyết định thiết kế ở `ChatLogCreate`/`ChatLogEntry` (app/schemas/chat_log.py).
    """
    document = log.model_dump()
    document["created_at"] = datetime.now(timezone.utc)
    mongo_db[CHAT_LOGS_COLLECTION].insert_one(document)


def load_session_history(mongo_db: MongoDatabase, session_id: str) -> list[BaseMessage]:
    """Đọc lại lịch sử phiên từ `chat_logs` (task 6.1.2, quyết định "nhớ toàn
    phiên") - CHỈ role `user`/`assistant` (bỏ qua `system`/`tool` nếu có,
    không phải nội dung hội thoại thật cần đưa vào ngữ cảnh LLM).

    Query lấy `MAX_HISTORY_MESSAGES` document MỚI NHẤT (sort `created_at`
    GIẢM DẦN + `limit`) RỒI MỚI đảo lại đúng thứ tự cũ->mới - hiệu quả hơn
    hẳn so với đọc TOÀN BỘ phiên rồi cắt bằng Python (phiên dài không tốn
    băng thông/bộ nhớ đọc những tin nhắn sẽ bị bỏ đi ngay sau đó). Xem giải
    thích ngưỡng `MAX_HISTORY_MESSAGES` ở đầu file.
    """
    cursor = (
        mongo_db[CHAT_LOGS_COLLECTION]
        .find({"session_id": session_id, "role": {"$in": ["user", "assistant"]}})
        .sort("created_at", -1)
        .limit(MAX_HISTORY_MESSAGES)
    )
    docs = list(cursor)
    docs.reverse()

    history: list[BaseMessage] = []
    for doc in docs:
        if doc["role"] == "user":
            history.append(HumanMessage(content=doc["message"]))
        else:
            history.append(AIMessage(content=doc["message"]))
    return history


async def stream_agent_reply(mongo_db: MongoDatabase, session_id: str, user_message: str) -> AsyncIterator[str]:
    """Ghép system prompt + lịch sử phiên (đã cắt bớt, KHÔNG gồm tin nhắn
    user hiện tại - tin đó truyền riêng qua `user_message`, chưa kịp lưu vào
    Mongo tại thời điểm hàm này chạy) thành ngữ cảnh đầy đủ, stream phản hồi
    LLM theo từng chunk text.

    Router (`app/routers/ai_chat.py`) gọi hàm NÀY thay vì gọi thẳng
    `astream_llm()` - giữ toàn bộ logic "hội thoại" (system prompt/lịch sử)
    ở tầng service, `app/core/llm.py` chỉ lo phần hạ tầng LLM thuần túy,
    không biết gì về `chat_logs`/session.
    """
    history = await asyncio.to_thread(load_session_history, mongo_db, session_id)
    messages: list[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT), *history, HumanMessage(content=user_message)]
    async for chunk in astream_llm(messages):
        yield chunk
