"""Router: AI Agent / Chat Module (`/ai`, WebSocket `/ws`).

Khung endpoint theo docs/API_SPEC.md - mục 8. Logic AI Agent (LangChain) thật
sẽ implement ở các task liên quan AI Agent / WebSocket.

Lưu ý: OpenAPI (Swagger) KHÔNG hỗ trợ mô tả route WebSocket - endpoint `/ws/chat`
sẽ không xuất hiện trên Swagger UI dù đã được include vào app (giới hạn của
chuẩn OpenAPI, không phải lỗi cấu hình).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket, status

from app.core.openapi_responses import auth_responses, rate_limit_response
from app.core.security import get_current_user
from app.schemas.ai_chat import ChatMessageCreate, ChatMessageRead, ChatReplyRead
from app.schemas.common import APIResponse

router = APIRouter(tags=["AI Agent / Chat"])


@router.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket) -> None:
    """Kênh WebSocket chat realtime giữa Customer và AI Agent.

    Yêu cầu: Customer (xác thực bằng token qua query string hoặc header khi connect).
    TODO: implement thật ở task AI Agent - xác thực token, gọi LangChain, rate limit (Redis).
    """
    await websocket.accept()
    await websocket.close(code=1011, reason="Chưa triển khai - sẽ hoàn thiện ở task AI Agent")


@router.post(
    "/ai/chat",
    response_model=APIResponse[ChatReplyRead],
    summary="(Fallback REST) Gửi tin nhắn tới AI Agent, nhận phản hồi",
    responses={**auth_responses(), **rate_limit_response()},
)
def send_chat_message(
    payload: ChatMessageCreate,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[ChatReplyRead]:
    """Fallback REST khi không dùng WebSocket. Yêu cầu: Customer. Có rate limit theo user (Redis)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task AI Agent")


@router.get(
    "/ai/chat/history",
    response_model=APIResponse[list[ChatMessageRead]],
    summary="Lịch sử hội thoại của user hiện tại",
    responses=auth_responses(),
)
def get_chat_history(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[list[ChatMessageRead]]:
    """Lịch sử hội thoại của user (từ MongoDB ChatLog). Yêu cầu: Customer."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task AI Agent")


@router.get(
    "/ai/chat/logs",
    response_model=APIResponse[list[ChatMessageRead]],
    summary="Xem log hội thoại toàn hệ thống",
    responses=auth_responses(forbidden=True),
)
def get_chat_logs(
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[list[ChatMessageRead]]:
    """Xem log hội thoại toàn hệ thống (phục vụ tune prompt). Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task AI Agent")
