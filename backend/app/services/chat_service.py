"""Business logic: AI Chat (task 5.1.1) - lưu tin nhắn vào MongoDB `chat_logs`
+ tạo phản hồi placeholder (AI Agent thật CHƯA tồn tại, task 6.x sẽ thay thế
phần placeholder này).

Hàm ở đây SYNC (pymongo, quyết định task 3.2.3, xem app/core/database.py) -
nơi gọi (WebSocket handler async trong app/routers/ai_chat.py) PHẢI tự bọc
`asyncio.to_thread(...)`, KHÔNG tự làm ở đây - giữ service layer thuần sync,
đúng convention 100% sync hiện tại của mọi service khác (cart_service.py,
order_service.py...), không phụ thuộc asyncio.
"""

import uuid
from datetime import datetime, timezone

from pymongo.database import Database as MongoDatabase

from app.schemas.chat_log import ChatLogCreate

CHAT_LOGS_COLLECTION = "chat_logs"

# AI Agent thật (LangChain, task 6.x) sẽ thay thế hằng số này bằng logic gọi
# model thật - hiện tại /ws/chat CHỈ xây hạ tầng truyền tin + xác thực + lưu
# trữ (task 5.1.1), không có logic trả lời AI.
PLACEHOLDER_REPLY_MESSAGE = (
    "Tính năng AI đang được phát triển - tin nhắn của bạn đã được ghi nhận, "
    "sẽ có phản hồi thật khi AI Agent hoàn thiện."
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
