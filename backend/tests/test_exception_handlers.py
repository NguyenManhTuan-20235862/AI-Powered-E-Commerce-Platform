"""Test cho global exception handler + logging (task 1.4.2).

Dùng monkeypatch để giả lập SQLAlchemyError / lỗi chung ngay trong endpoint
POST /auth/register thật (không sửa code app chỉ để phục vụ test) - patch hàm
service mà router gọi tới (`auth_service.get_user_by_email`).
"""

import logging

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

VALID_PAYLOAD = {
    "email": "exc-handler-test@example.com",
    "password": "password123",
    "full_name": "Exception Handler Test",
}


# ---- 422 RequestValidationError ----


def test_missing_required_field_returns_structured_422(client: TestClient) -> None:
    response = client.post("/api/v1/auth/register", json={"password": "password123", "full_name": "No Email"})
    assert response.status_code == 422

    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "email" in body["message"]


def test_validation_error_does_not_leak_submitted_value(client: TestClient) -> None:
    """Password quá ngắn (dưới min_length=8) - message phải nêu field "password"
    nhưng KHÔNG được echo lại giá trị plaintext client đã gửi."""
    payload = {**VALID_PAYLOAD, "password": "short1"}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422

    body = response.json()
    assert "password" in body["message"]
    assert "short1" not in response.text


def test_validation_error_logs_field_errors_with_request_id(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="app.main"):
        response = client.post("/api/v1/auth/register", json={"full_name": "No Email Or Password"})
    assert response.status_code == 422

    matching = [r for r in caplog.records if "Validation error" in r.getMessage()]
    assert matching, "Không thấy log warning cho validation error"
    assert matching[0].request_id != "-"


# ---- 500 SQLAlchemyError ----


def test_sqlalchemy_error_returns_generic_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_db_error(db, email):
        raise SQLAlchemyError("(pymysql.err.OperationalError) connection to mysql+pymysql://root:130905@host lost")

    monkeypatch.setattr("app.services.auth_service.get_user_by_email", _raise_db_error)

    response = client.post("/api/v1/auth/register", json=VALID_PAYLOAD)
    assert response.status_code == 500

    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error_code"] == "DATABASE_ERROR"
    assert body["message"] == "Lỗi hệ thống, vui lòng thử lại sau"
    # Không lộ connection string / password / chi tiết SQL thật ra response.
    assert "130905" not in response.text
    assert "mysql+pymysql" not in response.text


def test_sqlalchemy_error_logs_traceback_with_request_id(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def _raise_db_error(db, email):
        raise SQLAlchemyError("simulated deadlock")

    monkeypatch.setattr("app.services.auth_service.get_user_by_email", _raise_db_error)

    with caplog.at_level(logging.ERROR, logger="app.main"):
        response = client.post("/api/v1/auth/register", json=VALID_PAYLOAD)
    assert response.status_code == 500

    matching = [r for r in caplog.records if "Lỗi database" in r.getMessage()]
    assert matching, "Không thấy log error cho SQLAlchemyError"
    assert matching[0].request_id != "-"
    assert matching[0].exc_info is not None  # traceback thật có được log


# ---- 500 Exception chung (catch-all) ----


def test_unexpected_error_returns_generic_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_bug(db, email):
        raise RuntimeError("boom - unexpected bug with secret_internal_detail=42")

    monkeypatch.setattr("app.services.auth_service.get_user_by_email", _raise_bug)

    response = client.post("/api/v1/auth/register", json=VALID_PAYLOAD)
    assert response.status_code == 500

    body = response.json()
    assert body["success"] is False
    assert body["error_code"] == "INTERNAL_ERROR"
    assert body["message"] == "Lỗi hệ thống, vui lòng thử lại sau"
    assert "boom" not in response.text
    assert "secret_internal_detail" not in response.text
