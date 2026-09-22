"""Test WebSocket /ws/chat - xác thực (task 5.1.1) + luồng chat thật (task 6.1.2).

Phần XÁC THỰC (accept/reject đúng lúc handshake) - cùng phạm vi
`test_security.py`/`test_jwt_blacklist.py` (register+login thật qua HTTP,
MySQL/Redis thật, không mock).

Phần LUỒNG CHAT (task 6.1.2) - mock `chat_service.save_chat_log`/
`chat_service.stream_agent_reply` (KHÔNG cần MongoDB/LLM thật) để test
ĐÚNG HÀNH VI CỦA ROUTER (hình dạng giao thức `chunk`/`done`/`error`, lỗi LLM
không làm crash/đóng connection) tách biệt khỏi việc LLM có trả lời "đúng"
hay không - phần đó (nội dung AI trả lời thật, lưu MongoDB thật, nhớ ngữ
cảnh nhiều lượt thật) verify bằng browser/WS client thật ngoài pytest, xem
hướng dẫn verify trong PR (cần Ollama chạy thật, không phù hợp làm test tự
động xác định trước kết quả).

`TestClient.websocket_connect()` (Starlette) mở kết nối thật qua ASGI - nếu
server đóng kết nối TRƯỚC KHI accept (dependency raise `WebSocketException`,
xem app/routers/ai_chat.py:authenticate_websocket), context manager
`websocket_connect()` raise `WebSocketDisconnect` với đúng `.code` đã đóng -
đây là cách chuẩn FastAPI/Starlette test 1 WebSocket bị từ chối lúc handshake.
"""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy.orm import Session
from starlette.testclient import WebSocketDisconnect

from app.core.config import get_settings
from app.core.llm import LLMUnavailableError
from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole

VALID_PAYLOAD = {
    "email": "ws-chat-test@example.com",
    "password": "password123",
    "full_name": "WS Chat Test User",
}

ADMIN_PAYLOAD = {
    "email": "ws-chat-admin@example.com",
    "password": "password123",
    "full_name": "WS Chat Admin User",
}


def _register_and_login(client: TestClient, payload: dict) -> dict:
    client.post("/api/v1/auth/register", json=payload)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert response.status_code == 200
    return response.json()["data"]


def _expired_customer_token(user_id: int) -> str:
    """Tự ký token đã hết hạn - cùng pattern test_security.py:_expired_token()."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": "customer",
        "type": "access",
        "iat": now - timedelta(minutes=10),
        "exp": now - timedelta(minutes=5),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def test_no_token_rejected_4001(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/chat"):
            pass
    assert exc_info.value.code == 4001


def test_malformed_token_rejected_4001(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/api/v1/ws/chat?token=not-a-real-jwt"):
            pass
    assert exc_info.value.code == 4001


def test_expired_token_rejected_4001(client: TestClient) -> None:
    tokens = _register_and_login(client, VALID_PAYLOAD)
    # user_id thật lấy qua /auth/me (token còn hiệu lực) để ký token hết hạn
    # đúng user, không hardcode id đoán trước.
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    user_id = me.json()["data"]["id"]
    expired_token = _expired_customer_token(user_id)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/chat?token={expired_token}"):
            pass
    assert exc_info.value.code == 4001


def test_blacklisted_token_rejected_4001(client: TestClient) -> None:
    tokens = _register_and_login(client, VALID_PAYLOAD)
    access_token = tokens["access_token"]

    logout_response = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert logout_response.status_code == 200

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/chat?token={access_token}"):
            pass
    assert exc_info.value.code == 4001


def test_admin_token_rejected_4003(client: TestClient, db: Session) -> None:
    """`/ws/chat` CHỈ dành Customer (docs/API_SPEC.md mục 8) - Admin có token
    hợp lệ vẫn bị từ chối, NHƯNG với code khác (4003, không phải 4001) - phân
    biệt "sai role" với "chưa xác thực", đúng tinh thần 403 vs 401 của REST."""
    admin = User(
        email=ADMIN_PAYLOAD["email"],
        password_hash=hash_password(ADMIN_PAYLOAD["password"]),
        full_name=ADMIN_PAYLOAD["full_name"],
        role=UserRole.admin,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    admin_token = create_access_token(admin.id, admin.role.value)

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/api/v1/ws/chat?token={admin_token}"):
            pass
    assert exc_info.value.code == 4003


def test_valid_customer_token_connects_successfully(client: TestClient) -> None:
    tokens = _register_and_login(client, VALID_PAYLOAD)

    with client.websocket_connect(f"/api/v1/ws/chat?token={tokens['access_token']}") as ws:
        first_message = ws.receive_json()
        assert first_message["type"] == "connected"
        assert isinstance(first_message["session_id"], str) and first_message["session_id"]


CHAT_FLOW_PAYLOAD = {
    "email": "ws-chat-flow-test@example.com",
    "password": "password123",
    "full_name": "WS Chat Flow Test User",
}


def test_streaming_reply_sends_chunks_then_done(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Task 6.1.2 - mock `chat_service.save_chat_log`/`stream_agent_reply` để
    xác nhận ĐÚNG hình dạng giao thức: N `{"type": "chunk", ...}` liên tiếp
    rồi ĐÚNG 1 `{"type": "done"}`, không xen lẫn/thiếu."""
    monkeypatch.setattr("app.services.chat_service.save_chat_log", lambda mongo_db, log: None)

    async def fake_stream_agent_reply(mongo_db, session_id, user_message):
        for part in ["Xin", " chào", "!"]:
            yield part

    monkeypatch.setattr("app.services.chat_service.stream_agent_reply", fake_stream_agent_reply)

    tokens = _register_and_login(client, CHAT_FLOW_PAYLOAD)
    with client.websocket_connect(f"/api/v1/ws/chat?token={tokens['access_token']}") as ws:
        ws.receive_json()  # "connected"

        ws.send_json({"message": "Xin chào"})

        assert ws.receive_json() == {"type": "chunk", "content": "Xin"}
        assert ws.receive_json() == {"type": "chunk", "content": " chào"}
        assert ws.receive_json() == {"type": "chunk", "content": "!"}
        assert ws.receive_json() == {"type": "done"}


def test_llm_unavailable_sends_error_and_keeps_connection_usable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task 6.1.2, quyết định 3 - `LLMUnavailableError` (Ollama không chạy/
    timeout token đầu) PHẢI báo lỗi rõ ràng qua WebSocket, KHÔNG đóng
    connection - gửi tiếp tin nhắn khác vẫn hoạt động bình thường."""
    monkeypatch.setattr("app.services.chat_service.save_chat_log", lambda mongo_db, log: None)

    async def failing_stream_agent_reply(mongo_db, session_id, user_message):
        raise LLMUnavailableError("giả lập LLM không kết nối được")
        yield  # noqa: unreachable - bắt buộc để hàm là async generator hợp lệ

    monkeypatch.setattr("app.services.chat_service.stream_agent_reply", failing_stream_agent_reply)

    tokens = _register_and_login(client, CHAT_FLOW_PAYLOAD)
    with client.websocket_connect(f"/api/v1/ws/chat?token={tokens['access_token']}") as ws:
        ws.receive_json()  # "connected"

        ws.send_json({"message": "Xin chào"})
        assert ws.receive_json() == {"type": "error", "message": "Trợ lý đang bận, vui lòng thử lại sau"}

        # Kết nối VẪN dùng được sau lỗi - không bị đóng.
        ws.send_json({"message": "Thử lại lần nữa"})
        assert ws.receive_json() == {"type": "error", "message": "Trợ lý đang bận, vui lòng thử lại sau"}
