"""Pydantic schemas: AI Agent / Chat (request & response models).

TODO (Thành viên A - task AI Agent): hoàn thiện field thật khi tích hợp LangChain.
"""

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
