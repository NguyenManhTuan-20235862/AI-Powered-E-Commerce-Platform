"""Router: AI Agent (LangChain, tool calling).

TODO (Thành viên A): endpoint gọi AI Agent (tư vấn sản phẩm, tìm kiếm ngữ nghĩa),
có thể trả về dạng streaming (SSE) khi tích hợp LangChain thật.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/ai", tags=["AI Agent"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Route kiểm tra router AI Agent đã được include đúng."""
    return {"module": "ai_agent", "status": "ok"}
