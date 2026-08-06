"""Router: User Module (`/users`).

Khung endpoint theo docs/API_SPEC.md - mục 2.

Lưu ý: file này không nằm trong danh sách được liệt kê ban đầu ở task 1.2.2,
nhưng module User có trong docs/API_SPEC.md (mục 2) nên vẫn được tạo để Swagger
không thiếu nhóm endpoint - xem mục "còn thiếu/chưa rõ" để xác nhận lại.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user
from app.schemas.common import APIResponse, MessageResponse, PaginatedData
from app.schemas.user import ChangePasswordRequest, UserResponse, UserStatusUpdate, UserUpdate

router = APIRouter(prefix="/users", tags=["User"])


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Xem thông tin cá nhân",
    responses=auth_responses(),
)
def get_my_profile(current_user: Annotated[dict, Depends(get_current_user)]) -> APIResponse[UserResponse]:
    """Xem thông tin cá nhân. Yêu cầu: Customer, Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.put(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Cập nhật thông tin cá nhân",
    responses=auth_responses(),
)
def update_my_profile(
    payload: UserUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[UserResponse]:
    """Cập nhật thông tin cá nhân (tên, SĐT, địa chỉ). Yêu cầu: Customer, Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.put(
    "/me/password",
    response_model=MessageResponse,
    summary="Đổi mật khẩu",
    responses=auth_responses(),
)
def change_my_password(
    payload: ChangePasswordRequest,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> MessageResponse:
    """Đổi mật khẩu. Yêu cầu: Customer, Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.get(
    "",
    response_model=APIResponse[PaginatedData[UserResponse]],
    summary="Danh sách toàn bộ user",
    responses=auth_responses(forbidden=True),
)
def list_users(current_user: Annotated[dict, Depends(get_current_user)]) -> APIResponse[PaginatedData[UserResponse]]:
    """Danh sách toàn bộ user (phân trang, filter). Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.get(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="Xem chi tiết 1 user",
    responses=auth_responses(forbidden=True, not_found=True),
)
def get_user(
    user_id: str,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[UserResponse]:
    """Xem chi tiết 1 user. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.put(
    "/{user_id}/status",
    response_model=APIResponse[UserResponse],
    summary="Khóa/mở khóa tài khoản user",
    responses=auth_responses(forbidden=True, not_found=True),
)
def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    current_user: Annotated[dict, Depends(get_current_user)],
) -> APIResponse[UserResponse]:
    """Khóa/mở khóa tài khoản user. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")
