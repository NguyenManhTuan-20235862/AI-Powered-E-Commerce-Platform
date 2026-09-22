"""Test `app/core/llm.py` (task 6.1.1) - xác nhận kết nối LLM THẬT (gọi "Xin
chào" -> nhận phản hồi thật). SKIP (KHÔNG FAIL) nếu gọi thất bại - LLM là
dependency NGOÀI (Ollama local hoặc OpenAI thật, tùy `LLM_*` đang trỏ đâu),
có thể chưa chạy/chưa cấu hình đúng lúc `pytest -q` chạy trên máy khác hoặc
CI chưa cài Ollama - KHÁC các service nội bộ bắt buộc (MySQL/MongoDB/Redis,
`conftest.py` đã tự dựng), không nên làm cả test suite đỏ chỉ vì thiếu 1
dependency ngoài không liên quan tới logic ứng dụng đang test.
"""

import pytest

from app.core.llm import LLMUnavailableError, ask_llm


def test_ask_llm_returns_real_response_or_skips_if_unavailable() -> None:
    try:
        response = ask_llm("Xin chào")
    except LLMUnavailableError as exc:
        pytest.skip(f"LLM không kết nối được (Ollama/OpenAI chưa sẵn sàng) - bỏ qua: {exc}")

    assert isinstance(response, str)
    assert response.strip() != ""
