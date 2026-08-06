"""Pydantic schemas: AI Agent / Chat (request & response models).

TODO (Thành viên A - task AI Agent): hoàn thiện field thật khi tích hợp LangChain.
"""

from pydantic import BaseModel


class ChatMessageCreate(BaseModel):
    message: str


class ChatMessageRead(BaseModel):
    role: str
    content: str
    created_at: str


class ChatReplyRead(BaseModel):
    reply: str
