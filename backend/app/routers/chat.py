"""Router: Chat realtime (WebSocket) + lưu lịch sử chat vào MongoDB.

TODO (Thành viên A): endpoint WebSocket /chat/ws/{session_id}, lưu chat log vào MongoDB,
kết nối tới AI Agent (app.routers.ai_agent / app.services) để trả lời.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Route kiểm tra router Chat đã được include đúng."""
    return {"module": "chat", "status": "ok"}
