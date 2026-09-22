"""Test `app/services/chat_service.py` (task 6.1.2 - agent chat thật).

3 nhóm test:
1. `load_session_history()` - logic cắt bớt lịch sử phiên (MOCK `mongo_db`,
   KHÔNG cần MongoDB thật - đây là test logic truy vấn/map dữ liệu thuần,
   không phải test hành vi MongoDB thật).
2. `stream_agent_reply()` ghép đúng system prompt + lịch sử + tin nhắn mới
   (MOCK CẢ `mongo_db` LẪN `astream_llm` - kiểm tra đúng WIRING, không phụ
   thuộc LLM thật trả lời "thông minh" hay không).
3. `stream_agent_reply()` gọi LLM THẬT, trả chunk thật - SKIP (không FAIL)
   nếu LLM không kết nối được, cùng pattern `test_llm.py` (task 6.1.1) - LLM
   là dependency NGOÀI, có thể chưa chạy trên máy/CI khác.

KHÔNG dùng `pytest-asyncio` (chưa có trong `requirements-test.txt`, và đây
là hàm `async def`/async generator ĐẦU TIÊN cần test trong dự án) - dùng
`asyncio.run()` bọc quanh 1 hàm `async def` nội bộ trong mỗi test SYNC bình
thường, tránh thêm dependency mới chỉ cho vài test này.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import SystemMessage

from app.core.llm import LLMUnavailableError
from app.core.database import get_mongo_db
from app.services.chat_service import MAX_HISTORY_MESSAGES, load_session_history, stream_agent_reply


def test_load_session_history_keeps_only_last_n_messages_in_chronological_order() -> None:
    """Giả lập Mongo có NHIỀU HƠN `MAX_HISTORY_MESSAGES` tin nhắn cho 1 phiên -
    mock đúng hành vi truy vấn thật (`.sort("created_at", -1).limit(N)` trả
    về N tin MỚI NHẤT, thứ tự GIẢM DẦN) - xác nhận hàm đảo lại đúng thứ tự cũ
    -> mới VÀ chỉ giữ đúng N tin (không phải đọc hết rồi cắt bằng Python)."""
    # 20 tin mới nhất (giả lập query thật đã trả về, GIẢM DẦN: msg-24 .. msg-5)
    docs_desc = [
        {"role": "user" if i % 2 == 0 else "assistant", "message": f"msg-{i}"} for i in range(24, 4, -1)
    ]
    assert len(docs_desc) == MAX_HISTORY_MESSAGES

    mongo_db = MagicMock()
    find_mock = mongo_db.__getitem__.return_value.find
    find_mock.return_value.sort.return_value.limit.return_value = docs_desc

    history = load_session_history(mongo_db, "sess-truncate")

    # Đúng collection + filter + sort + limit đã dùng.
    mongo_db.__getitem__.assert_called_with("chat_logs")
    find_mock.assert_called_with({"session_id": "sess-truncate", "role": {"$in": ["user", "assistant"]}})
    find_mock.return_value.sort.assert_called_with("created_at", -1)
    find_mock.return_value.sort.return_value.limit.assert_called_with(MAX_HISTORY_MESSAGES)

    # Đúng số lượng, đúng thứ tự CŨ -> MỚI sau khi đảo (msg-5 cũ nhất trong 20
    # tin giữ lại, msg-24 mới nhất) - KHÔNG có msg-0..msg-4 (đã bị cắt bớt).
    assert len(history) == MAX_HISTORY_MESSAGES
    assert [m.content for m in history] == [f"msg-{i}" for i in range(5, 25)]


def test_load_session_history_maps_role_to_correct_message_type() -> None:
    # Mock GIẢ ĐÚNG hành vi truy vấn thật (.sort("created_at", -1) - GIẢM DẦN,
    # tức MỚI NHẤT trước) - "Trả lời cũ" (assistant) MỚI hơn "Câu hỏi cũ"
    # (user) nên đứng TRƯỚC trong mock; hàm dưới test sẽ tự đảo lại đúng thứ
    # tự cũ -> mới (user hỏi trước, assistant trả lời sau).
    mongo_db = MagicMock()
    mongo_db.__getitem__.return_value.find.return_value.sort.return_value.limit.return_value = [
        {"role": "assistant", "message": "Trả lời cũ"},
        {"role": "user", "message": "Câu hỏi cũ"},
    ]

    history = load_session_history(mongo_db, "sess-role-map")

    # Sau khi đảo: user (Câu hỏi cũ) đứng TRƯỚC assistant (Trả lời cũ).
    assert type(history[0]).__name__ == "HumanMessage"
    assert history[0].content == "Câu hỏi cũ"
    assert type(history[1]).__name__ == "AIMessage"
    assert history[1].content == "Trả lời cũ"


def test_stream_agent_reply_includes_system_prompt_and_session_history() -> None:
    """Kiểm tra ĐÚNG WIRING (task 6.1.2, quyết định "nhớ toàn phiên") - mock
    `astream_llm` để bắt lại CHÍNH XÁC danh sách message đã ghép, không phụ
    thuộc LLM thật trả lời đúng/sai."""
    # Mock GIẢM DẦN (mới nhất trước, đúng hành vi truy vấn thật) - xem giải
    # thích thứ tự ở test_load_session_history_maps_role_to_correct_message_type.
    mongo_db = MagicMock()
    mongo_db.__getitem__.return_value.find.return_value.sort.return_value.limit.return_value = [
        {"role": "assistant", "message": "Trả lời cũ"},
        {"role": "user", "message": "Câu hỏi cũ"},
    ]

    captured_messages: list = []

    async def fake_astream_llm(messages):
        captured_messages.extend(messages)
        yield "phản hồi mới"

    async def run() -> list[str]:
        chunks = []
        with patch("app.services.chat_service.astream_llm", fake_astream_llm):
            async for chunk in stream_agent_reply(mongo_db, "sess-wiring", "Câu hỏi mới"):
                chunks.append(chunk)
        return chunks

    chunks = asyncio.run(run())

    assert chunks == ["phản hồi mới"]
    assert len(captured_messages) == 4
    assert isinstance(captured_messages[0], SystemMessage)
    assert captured_messages[1].content == "Câu hỏi cũ"
    assert captured_messages[2].content == "Trả lời cũ"
    assert captured_messages[3].content == "Câu hỏi mới"


def test_stream_agent_reply_raises_llm_unavailable_without_crashing() -> None:
    """`stream_agent_reply()` PHẢI để lộ nguyên `LLMUnavailableError` ra ngoài
    (không tự nuốt/che lỗi) - nơi gọi (router) mới là chỗ quyết định cách xử
    lý (task 6.1.2, quyết định 3: báo lỗi rõ ràng, không crash connection)."""
    mongo_db = MagicMock()
    mongo_db.__getitem__.return_value.find.return_value.sort.return_value.limit.return_value = []

    async def failing_astream_llm(messages):
        raise LLMUnavailableError("giả lập LLM không kết nối được")
        yield  # noqa: unreachable - bắt buộc để hàm là async generator hợp lệ

    async def run() -> None:
        with patch("app.services.chat_service.astream_llm", failing_astream_llm):
            async for _ in stream_agent_reply(mongo_db, "sess-error", "Xin chào"):
                pass

    with pytest.raises(LLMUnavailableError):
        asyncio.run(run())


def test_stream_agent_reply_returns_real_chunks_or_skips_if_unavailable() -> None:
    """LLM THẬT - session_id ngẫu nhiên/không tồn tại (lịch sử rỗng, hàm CHỈ
    ĐỌC Mongo, KHÔNG ghi gì) nên an toàn dùng thẳng `get_mongo_db()` thật,
    không cần dọn dữ liệu sau test."""
    mongo_db = get_mongo_db()

    async def run() -> str:
        chunks = []
        async for chunk in stream_agent_reply(mongo_db, "test-session-no-history", "Xin chào"):
            chunks.append(chunk)
        return "".join(chunks)

    try:
        full_reply = asyncio.run(run())
    except LLMUnavailableError as exc:
        pytest.skip(f"LLM không kết nối được (Ollama/OpenAI chưa sẵn sàng) - bỏ qua: {exc}")

    assert full_reply.strip() != ""
