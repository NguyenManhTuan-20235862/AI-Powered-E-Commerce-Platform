"""Test cho RequestContextMiddleware (task 1.4.2 - item 3)."""

import logging

import pytest
from fastapi.testclient import TestClient


def test_response_has_request_id_header(client: TestClient) -> None:
    response = client.get("/health")
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


def test_incoming_request_id_is_reused(client: TestClient) -> None:
    """Nếu client tự gửi X-Request-ID (VD: gateway/tracing hệ thống ngoài), giữ
    nguyên giá trị đó thay vì tự sinh UUID mới - để trace xuyên suốt nhiều service."""
    response = client.get("/health", headers={"X-Request-ID": "trace-abc-123"})
    assert response.headers["x-request-id"] == "trace-abc-123"


def test_successful_request_is_logged(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="app.core.middleware"):
        response = client.get("/health")
    assert response.status_code == 200

    matching = [r for r in caplog.records if "GET /health" in r.getMessage()]
    assert matching, "Không thấy log cho request thành công"
    assert "200" in matching[0].getMessage()
    assert matching[0].request_id != "-"


def test_different_requests_get_different_request_ids(client: TestClient) -> None:
    first = client.get("/health").headers["x-request-id"]
    second = client.get("/health").headers["x-request-id"]
    assert first != second
