"""Test cho schema dùng chung app/schemas/common.py (task 1.4.1)."""

import pytest
from pydantic import ValidationError

from app.schemas.common import (
    APIResponse,
    ErrorResponse,
    MessageResponse,
    PaginationParams,
    paginated_response,
    success_response,
)


def test_api_response_defaults() -> None:
    response = APIResponse[str](data="hello")
    assert response.success is True
    assert response.data == "hello"
    assert response.message == ""


def test_success_response_helper() -> None:
    response = success_response(data={"id": 1}, message="OK")
    assert response.success is True
    assert response.data == {"id": 1}
    assert response.message == "OK"


def test_error_response_defaults() -> None:
    error = ErrorResponse(message="Không tìm thấy")
    assert error.success is False
    assert error.data is None
    assert error.message == "Không tìm thấy"
    assert error.error_code is None


def test_pagination_params_defaults() -> None:
    params = PaginationParams()
    assert params.page == 1
    assert params.page_size == 20


def test_pagination_params_rejects_invalid_page() -> None:
    with pytest.raises(ValidationError):
        PaginationParams(page=0)


def test_pagination_params_rejects_page_size_over_limit() -> None:
    with pytest.raises(ValidationError):
        PaginationParams(page_size=101)


def test_paginated_response_helper_computes_total_pages() -> None:
    result = paginated_response(items=[1, 2, 3], total=23, page=1, page_size=10)
    assert result.items == [1, 2, 3]
    assert result.total == 23
    assert result.page_size == 10
    assert result.total_pages == 3  # ceil(23 / 10)


def test_paginated_response_helper_zero_total() -> None:
    result = paginated_response(items=[], total=0, page=1, page_size=20)
    assert result.total_pages == 0


def test_message_response_defaults() -> None:
    msg = MessageResponse()
    assert msg.success is True
    assert msg.message == ""
