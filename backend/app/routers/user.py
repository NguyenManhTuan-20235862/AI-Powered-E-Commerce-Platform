"""Router: User Module (`/users`).

Khung endpoint theo docs/API_SPEC.md - mục 2.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, MessageResponse, PaginatedResponse, success_response
from app.schemas.user import ChangePasswordRequest, UserResponse, UserStatusUpdate, UserUpdate

router = APIRouter(prefix="/users", tags=["User"])


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Xem thông tin cá nhân",
    responses=auth_responses(),
)
def get_my_profile(current_user: Annotated[User, Depends(get_current_user)]) -> APIResponse[UserResponse]:
    """Xem thông tin cá nhân. Yêu cầu: Customer, Admin.

    Ví dụ minh họa cách dùng response_model=APIResponse[T] + success_response()
    (task 1.4.1) - current_user đã là chính user cần trả về (get_current_user
    load từ DB rồi) nên không cần query gì thêm, không phải dữ liệu giả.
    """
    return success_response(data=UserResponse.model_validate(current_user))


@router.put(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Cập nhật thông tin cá nhân",
    responses=auth_responses(),
)
def update_my_profile(
    payload: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
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
    current_user: Annotated[User, Depends(get_current_user)],
) -> MessageResponse:
    """Đổi mật khẩu. Yêu cầu: Customer, Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")


@router.get(
    "",
    response_model=APIResponse[PaginatedResponse[UserResponse]],
    summary="Danh sách toàn bộ user",
    responses=auth_responses(forbidden=True),
)
def list_users(
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> APIResponse[PaginatedResponse[UserResponse]]:
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
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
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
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
) -> APIResponse[UserResponse]:
    """Khóa/mở khóa tài khoản user. Yêu cầu: Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai")
