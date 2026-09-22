"""Router: AI Agent / Chat Module (`/ai`, WebSocket `/ws`).

Khung endpoint theo docs/API_SPEC.md - mục 8. Logic AI Agent (LangChain) thật
sẽ implement ở task 6.x.

Lưu ý: OpenAPI (Swagger) KHÔNG hỗ trợ mô tả route WebSocket - endpoint `/ws/chat`
sẽ không xuất hiện trên Swagger UI dù đã được include vào app (giới hạn của
chuẩn OpenAPI, không phải lỗi cấu hình).

`/ws/chat` (task 5.1.1) - xác thực qua JWT truyền ở QUERY PARAM (`?token=...`),
KHÔNG PHẢI Authorization header như REST - trình duyệt không cho set custom
header lúc mở WebSocket handshake. Đánh đổi đã xác nhận: token lộ trong access
log (khác header, không tự ẩn) - chấp nhận vì access token sống ngắn (60 phút),
đã ghi `docs/KNOWN_TODOS.md` #27 (cần redact log khi có logging tập trung
thật, task 7.5). Dùng LẠI đúng `get_token_payload`/`get_current_user`
(app/core/security.py) - gọi TRỰC TIẾP như hàm Python thường (annotation
`Depends()` trên tham số của 2 hàm đó chỉ có tác dụng khi FastAPI tự inject
qua HTTP, gọi thẳng bằng vị trí/keyword vẫn chạy đúng logic y hệt), KHÔNG viết
lại decode/blacklist. Cả 2 lệnh gọi Mongo (pymongo, sync) VÀ Redis (redis-py,
sync, qua is_token_blacklisted bên trong get_current_user) đều PHẢI bọc
`asyncio.to_thread(...)` khi gọi từ handler async này - gọi trực tiếp sẽ block
event loop, ảnh hưởng MỌI WebSocket connection khác đang chạy chung process
(xem app/core/database.py, đã note sẵn cho cả 2 client).

AI Agent thật (task 6.1.2, `app/services/chat_service.py:stream_agent_reply()`)
- nhận tin nhắn user -> lưu `chat_logs` -> stream phản hồi LLM theo từng
chunk qua WebSocket (giao thức `chunk`/`done`/`error`, KHÔNG PHẢI `reply` 1
lần như bản placeholder cũ) -> lưu full message assistant vào `chat_logs`
khi stream xong. CHƯA có RAG/tool query DB thật (task 6.2/6.3) - system
prompt (chat_service.py) tự giới hạn phạm vi trả lời, không bịa giá/tồn kho
sản phẩm cụ thể. Rate limit (task 8.3) CHƯA làm - biết trước rủi ro (ai cũng
gọi được, tốn tài nguyên vô tội vạ với AI Agent thật đã tốn chi phí/tài
nguyên tính toán hơn hẳn placeholder cũ) nhưng để dành task riêng, đúng
KNOWN_TODOS #2 (xem docs/KNOWN_TODOS.md).
"""

import asyncio
import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
from pydantic import ValidationError
from pymongo.database import Database as MongoDatabase
from redis import Redis
from sqlalchemy.orm import Session

from app.core.database import get_db, get_mongo_db, get_redis
from app.core.llm import LLMUnavailableError
from app.core.openapi_responses import auth_responses, rate_limit_response
from app.core.security import get_current_user, get_token_payload, require_role
from app.models.user import User, UserRole
from app.schemas.ai_chat import ChatMessageCreate, ChatMessageRead, ChatReplyRead
from app.schemas.chat_log import ChatLogCreate
from app.schemas.common import APIResponse
from app.services import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI Agent / Chat"])

# Close code tự định nghĩa (RFC 6455 dành riêng dải 4000-4999 cho ứng dụng) -
# đặt trùng số với HTTP 401/403 tương ứng cho dễ nhớ/tra cứu, bản thân spec WS
# không yêu cầu 2 con số phải khớp nhau.
WS_CLOSE_UNAUTHORIZED = 4001
WS_CLOSE_FORBIDDEN = 4003


def _decode_and_load_user(token: str, db: Session, redis_client: Redis) -> User:
    """Chạy trong `asyncio.to_thread` - gọi LẠI đúng logic decode JWT +
    check blacklist Redis + load User MySQL đã có ở app/core/security.py,
    KHÔNG viết lại. Raise `HTTPException(401)` y hệt đường REST nếu thiếu/
    sai/hết hạn/blacklist/tài khoản khoá."""
    payload = get_token_payload(token)
    return get_current_user(payload, db, redis_client)


async def authenticate_websocket(
    websocket: WebSocket,
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[Redis, Depends(get_redis)],
    token: Annotated[str | None, Query(description="Access token JWT, VD: ?token=<access_token>")] = None,
) -> User:
    """Dependency xác thực WebSocket (task 5.1.1) - raise `WebSocketException`
    thay vì `HTTPException`: FastAPI tự đóng kết nối đúng close code TRƯỚC KHI
    endpoint handler chạy (kể cả trước `websocket.accept()`), không cần tự gọi
    accept()/close() thủ công ở đây - pattern chính thức FastAPI hỗ trợ cho
    WebSocket auth qua dependency (từ 0.92, dự án dùng 0.115.6).

    4001 (thiếu/sai/hết hạn/blacklist token) tách riêng với 4003 (token hợp lệ
    nhưng không phải Customer) - đúng tinh thần phân biệt 401 vs 403 đã dùng
    cho REST (`get_current_user` vs `require_role`), API_SPEC.md mục 8 quy
    định `/ws/chat` CHỈ dành cho Customer.
    """
    if not token:
        raise WebSocketException(code=WS_CLOSE_UNAUTHORIZED, reason="Thiếu token xác thực")

    try:
        user = await asyncio.to_thread(_decode_and_load_user, token, db, redis_client)
    except HTTPException:
        raise WebSocketException(code=WS_CLOSE_UNAUTHORIZED, reason="Token không hợp lệ hoặc đã hết hạn")

    if user.role != UserRole.customer:
        raise WebSocketException(code=WS_CLOSE_FORBIDDEN, reason="Chỉ Customer được dùng kênh chat AI")

    return user


@router.websocket("/ws/chat")
async def chat_websocket(
    websocket: WebSocket,
    current_user: Annotated[User, Depends(authenticate_websocket)],
    mongo_db: Annotated[MongoDatabase, Depends(get_mongo_db)],
) -> None:
    """Kênh WebSocket chat realtime giữa Customer và AI Agent (task 5.1.1,
    agent thật task 6.1.2).

    Vòng đời: accept -> gửi `{"type": "connected", "session_id": ...}` -> lặp
    nhận/lưu/stream phản hồi tới khi client ngắt kết nối hoặc lỗi. Tin nhắn
    sai định dạng (không phải JSON, hoặc JSON nhưng sai schema
    `ChatMessageCreate`) KHÔNG làm crash connection - chỉ gửi
    `{"type": "error", ...}` lại đúng client đó rồi tiếp tục vòng lặp. Lỗi hạ
    tầng (Mongo insert thất bại) cũng được bắt riêng, không để crash
    connection.

    Giao thức phản hồi (task 6.1.2, thay hẳn `reply` 1 lần của bản placeholder
    cũ): 0..N `{"type": "chunk", "content": "..."}` (mỗi mảnh text AI sinh ra)
    rồi `{"type": "done"}` (báo stream xong) - HOẶC `{"type": "error", ...}`
    nếu LLM lỗi/treo giữa chừng (KHÔNG gửi `done` trong trường hợp này).
    """
    await websocket.accept()
    session_id = chat_service.new_session_id()
    await websocket.send_json({"type": "connected", "session_id": session_id})

    try:
        while True:
            try:
                raw = await websocket.receive_json()
            except ValueError:
                await websocket.send_json({"type": "error", "message": "Tin nhắn phải là JSON hợp lệ"})
                continue

            try:
                payload = ChatMessageCreate.model_validate(raw)
            except ValidationError as exc:
                await websocket.send_json(
                    {"type": "error", "message": f"Tin nhắn không hợp lệ: {exc.errors()[0]['msg']}"}
                )
                continue

            try:
                user_log = ChatLogCreate(
                    user_id=current_user.id,
                    session_id=session_id,
                    role="user",
                    message=payload.message,
                )
                await asyncio.to_thread(chat_service.save_chat_log, mongo_db, user_log)
            except Exception:
                logger.exception("Lỗi lúc lưu tin nhắn user (user_id=%s, session_id=%s)", current_user.id, session_id)
                await websocket.send_json({"type": "error", "message": "Lỗi hệ thống - vui lòng thử lại"})
                continue

            reply_parts: list[str] = []
            try:
                async for chunk_text in chat_service.stream_agent_reply(mongo_db, session_id):
                    reply_parts.append(chunk_text)
                    await websocket.send_json({"type": "chunk", "content": chunk_text})
            except LLMUnavailableError:
                logger.warning(
                    "LLM không khả dụng lúc trả lời (user_id=%s, session_id=%s)", current_user.id, session_id
                )
                await websocket.send_json({"type": "error", "message": "Trợ lý đang bận, vui lòng thử lại sau"})
                continue

            full_reply = "".join(reply_parts).strip()
            if full_reply:
                try:
                    assistant_log = ChatLogCreate(
                        user_id=current_user.id,
                        session_id=session_id,
                        role="assistant",
                        message=full_reply,
                    )
                    await asyncio.to_thread(chat_service.save_chat_log, mongo_db, assistant_log)
                except Exception:
                    # Tin nhắn ĐÃ stream hết cho client rồi (chunk gửi xong) -
                    # chỉ log lỗi lưu trữ, KHÔNG báo lỗi cho user (họ đã nhận
                    # được câu trả lời, chỉ lịch sử phiên có thể thiếu tin
                    # nhắn này) - khác nhánh lỗi user_log ở trên (lúc đó CHƯA
                    # gửi gì cho user, phải báo lỗi thật).
                    logger.exception(
                        "Lỗi lúc lưu tin nhắn assistant (user_id=%s, session_id=%s)", current_user.id, session_id
                    )

            await websocket.send_json({"type": "done"})
    except WebSocketDisconnect:
        pass


@router.post(
    "/ai/chat",
    response_model=APIResponse[ChatReplyRead],
    summary="(Fallback REST) Gửi tin nhắn tới AI Agent, nhận phản hồi",
    responses={**auth_responses(forbidden=True), **rate_limit_response()},
)
def send_chat_message(
    payload: ChatMessageCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
) -> APIResponse[ChatReplyRead]:
    """Fallback REST khi không dùng WebSocket. Yêu cầu: Customer. Có rate limit theo user (Redis)."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task AI Agent")


@router.get(
    "/ai/chat/history",
    response_model=APIResponse[list[ChatMessageRead]],
    summary="Lịch sử hội thoại của user hiện tại",
    responses=auth_responses(forbidden=True),
)
def get_chat_history(
    current_user: Annotated[User, Depends(require_role(UserRole.customer))],
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
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> APIResponse[list[ChatMessageRead]]:
    """Xem log hội thoại toàn hệ thống (phục vụ tune prompt). Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task AI Agent")
