"""Pydantic schema: ChatLog (MongoDB collection `chat_logs`, task 3.2.1).

Đây là schema cho document MongoDB - KHÔNG kế thừa `BaseSchema`
(`app/schemas/base.py`, `from_attributes=True` dành riêng cho đọc từ đối
tượng SQLAlchemy ORM). Document MongoDB đọc về ở dạng `dict` (qua PyMongo,
`bson.ObjectId` cho `_id`) - `model_validate(dict)` hoạt động trực tiếp với
dict, không cần `from_attributes`.

QUYẾT ĐỊNH THIẾT KẾ (task 3.2.1) - 1 document / 1 TIN NHẮN, KHÔNG phải 1
document / 1 session (mảng messages lồng bên trong). Lý do:
  - Insert khớp tự nhiên với luồng ghi thật (task 5.1 WebSocket, 6.x AI
    Agent): mỗi tin nhắn tới thì insert 1 document ngay, không cần
    find-rồi-`$push` vào document session đang có (tránh round-trip đọc
    trước khi ghi, và tránh rủi ro vượt giới hạn 16MB/document của MongoDB
    nếu 1 session chat rất dài - khó xảy ra sớm nhưng là giới hạn cứng, thiết
    kế 1 doc/tin nhắn loại bỏ hẳn rủi ro này).
  - Query linh hoạt hơn cho cả 2 use case chính: `GET /ai/chat/history` (lịch
    sử theo user, phân trang theo `created_at`) và `GET /ai/chat/logs`
    (Admin duyệt TOÀN BỘ log để tune prompt, thường cần lọc/sắp xếp chéo
    nhiều user/session) - cả 2 đều là query phẳng trên field top-level
    (`user_id`, `session_id`, `created_at`), không cần `$unwind` aggregation
    như khi dữ liệu nằm trong mảng lồng.
  - `session_id` vẫn dùng để GOM NHÓM các tin nhắn cùng 1 phiên (dựng lại thứ
    tự hội thoại bằng query `{session_id: ...}` sort theo `created_at`) - chỉ
    là field thường trên từng document, không phải cấu trúc lồng vật lý.
  - Đánh đổi: nhiều document hơn (1 document/tin nhắn thay vì 1
    document/session) - chấp nhận được vì đây đúng là pattern "event log"
    MongoDB được thiết kế để xử lý tốt, và trùng lặp `user_id`/`session_id`
    trên mỗi document là chi phí không đáng kể so với lợi ích query.

user_id KHÔNG PHẢI foreign key thật (khác hệ CSDL - `users.id` ở MySQL,
`chat_logs.user_id` ở MongoDB) - MongoDB không biết và không enforce việc
`user_id` này có tồn tại thật trong bảng `users` hay không, và xóa 1 user ở
MySQL KHÔNG tự động xóa/cập nhật các document liên quan ở đây. Nếu nghiệp vụ
cần giữ toàn vẹn (VD: xóa user thật thì cũng nên xóa/ẩn chat log của họ), phải
tự xử lý ở tầng service (gọi thêm 1 lệnh xóa/cập nhật riêng trên
`chat_logs` khi xóa user) - KHÔNG có cơ chế nào tự động làm việc này.
"""

from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

# Pydantic v2: cách khuyến nghị hiện tại để nhận bson.ObjectId (từ document
# PyMongo trả về) và biểu diễn dưới dạng str trong model Python - BeforeValidator
# tự chạy str() lên giá trị TRƯỚC khi Pydantic validate như 1 str bình thường,
# nên nhận được cả bson.ObjectId (Mongo trả về) lẫn str có sẵn (VD khi build
# lại model từ response JSON) mà không lỗi. Đơn giản hơn hẳn cách viết custom
# type với __get_validators__/__modify_schema__ kiểu Pydantic v1 cũ.
PyObjectId = Annotated[str, BeforeValidator(str)]


class ChatLogBase(BaseModel):
    """Field chung cho 1 document `chat_logs` - dùng làm base cho cả lúc tạo
    mới (trước khi insert) lẫn lúc đọc về (sau khi insert, có thêm `_id`/`created_at`).
    """

    # int - khớp kiểu BIGINT của users.id bên MySQL (xem docstring module về
    # việc đây KHÔNG phải FK thật). KHÔNG dùng str để tránh phải convert qua
    # lại khi so sánh/join thủ công với dữ liệu từ MySQL ở tầng service.
    user_id: int
    # Do tầng service sinh ra (VD uuid4 khi bắt đầu 1 phiên WebSocket mới,
    # task 5.1/6.x quyết định chi tiết) - KHÔNG phải ObjectId, chỉ là chuỗi
    # định danh phiên chat để gom nhóm tin nhắn (xem quyết định thiết kế ở
    # docstring module).
    session_id: str
    # "system"/"tool" thêm sẵn dù task 3.2.1 chỉ cần "user"/"assistant" - vì
    # `metadata.tool_calls` (bên dưới) đã là field CHÍNH THỨC của task này
    # (phục vụ task 6.3 tool calling), và taxonomy role "user/assistant/
    # system/tool" là chuẩn hội thoại LLM phổ biến (OpenAI/LangChain) - khai
    # báo đủ ngay từ đầu để không phải sửa lại type này ở task 6.3, KHÔNG
    # phải suy đoán thêm nghiệp vụ ngoài phạm vi hiện tại.
    role: Literal["user", "assistant", "system", "tool"]
    message: str
    # Object linh hoạt: sản phẩm AI gợi ý kèm tin nhắn, tool_calls (task 6.3),
    # model/token usage... - cố tình KHÔNG khai báo field con cụ thể ở đây
    # (schema tối thiểu cho task 3.2.1, để ngỏ cho task 6.x quyết định cấu
    # trúc thật của tool_calls/gợi ý sản phẩm khi có code AI Agent thật).
    metadata: dict[str, Any] | None = None


class ChatLogCreate(ChatLogBase):
    """Dùng để validate dữ liệu TRƯỚC KHI insert vào MongoDB (task 3.2.3 kết
    nối PyMongo thật, task 5.1/6.x nơi thật sự gọi insert_one).

    KHÔNG có `_id`/`created_at` - `_id` do MongoDB tự sinh (ObjectId) lúc
    insert, `created_at` do tầng service set (`datetime.now(timezone.utc)`)
    ngay trước khi insert, không nhận từ input để đảm bảo phản ánh đúng thời
    điểm ghi thật.
    """


class ChatLogEntry(ChatLogBase):
    """Document đầy đủ đọc VỀ từ MongoDB - có `_id` (ObjectId, biểu diễn dưới
    dạng str qua `PyObjectId`) và `created_at`.

    Dùng làm response schema cho `GET /ai/chat/history` (lịch sử của user
    hiện tại) và `GET /ai/chat/logs` (Admin xem toàn bộ log) - xem
    `app/routers/ai_chat.py`. Router 2 endpoint này hiện vẫn `501` (chưa
    implement, task AI Agent) và đang tạm dùng `ChatMessageRead`
    (`app/schemas/ai_chat.py`, schema REST tối giản có sẵn từ trước) - việc
    nối 2 router đó sang dùng `ChatLogEntry` này (đầy đủ field hơn: `id`,
    `session_id`, `metadata`) thuộc phạm vi task 3.2.3/5.1/6.x, KHÔNG sửa ở
    task 3.2.1 (chỉ thiết kế document + schema tham chiếu).
    """

    id: PyObjectId = Field(alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # populate_by_name=True: cho phép khởi tạo bằng `id=...` (Python) lẫn
    # `_id=...` (đúng key thật trong document Mongo) - cần thiết vì Mongo trả
    # về dict có key `_id`, còn code Python thường muốn field tên `id` (không
    # có dấu `_` đầu, tránh xung đột với `BaseModel.dict()`/quy ước Python).
    model_config = ConfigDict(populate_by_name=True)
