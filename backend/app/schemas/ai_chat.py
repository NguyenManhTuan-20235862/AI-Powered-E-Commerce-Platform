"""Pydantic schemas: AI Agent / Chat (request & response models).

`ChatMessageCreate` dùng thật cho `/ws/chat` (task 5.1.1, agent thật task
6.1.2). `ChatMessageRead`/`ChatReplyRead` vẫn CHƯA dùng - dành cho fallback
REST `/ai/chat` và 2 endpoint lịch sử (`/ai/chat/history`, `/ai/chat/logs`),
hiện vẫn `501` (ngoài phạm vi task 6.1.2, chỉ làm kênh WebSocket)."""

from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    """Envelope tin nhắn client gửi lên qua `/ws/chat` (task 5.1.1) - dùng
    CHUNG cho cả WebSocket lẫn fallback REST `/ai/chat` sau này.

    `max_length=2000` - giới hạn cơ bản chặn 1 tin nhắn khổng lồ, KHÔNG PHẢI
    rate limiting thật (để dành task 8.3, xem docs/API_SPEC.md mục 8).
    """

    message: str = Field(min_length=1, max_length=2000)


class ChatMessageRead(BaseModel):
    role: str
    content: str
    created_at: str


class ChatReplyRead(BaseModel):
    reply: str
