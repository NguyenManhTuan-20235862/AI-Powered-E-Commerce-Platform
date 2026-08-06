"""Các mẫu `responses=` dùng chung cho Swagger docs (mã lỗi phổ biến 401/403/404/429)."""

from typing import Any

_UNAUTHORIZED: dict[int | str, dict[str, Any]] = {
    401: {"description": "Chưa đăng nhập hoặc token không hợp lệ/hết hạn"},
}

_FORBIDDEN: dict[int | str, dict[str, Any]] = {
    403: {"description": "Không đủ quyền truy cập (sai role)"},
}

_NOT_FOUND: dict[int | str, dict[str, Any]] = {
    404: {"description": "Không tìm thấy tài nguyên"},
}

_RATE_LIMITED: dict[int | str, dict[str, Any]] = {
    429: {"description": "Vượt quá giới hạn tần suất (rate limit) - thử lại sau"},
}


def auth_responses(*, forbidden: bool = False, not_found: bool = False) -> dict[int | str, dict[str, Any]]:
    """Ghép các response lỗi phổ biến cho endpoint cần đăng nhập (`Depends(get_current_user)`).

    - Luôn có 401 (chưa đăng nhập / token không hợp lệ).
    - `forbidden=True`: thêm 403 (endpoint chỉ dành cho 1 role cụ thể, VD Admin).
    - `not_found=True`: thêm 404 (endpoint thao tác trên tài nguyên theo ID).
    """
    responses: dict[int | str, dict[str, Any]] = dict(_UNAUTHORIZED)
    if forbidden:
        responses.update(_FORBIDDEN)
    if not_found:
        responses.update(_NOT_FOUND)
    return responses


def rate_limit_response() -> dict[int | str, dict[str, Any]]:
    """Response 429 cho các endpoint có giới hạn tần suất (VD `/ai/chat`, `/ws/chat`)."""
    return dict(_RATE_LIMITED)
