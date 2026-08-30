"""Router: User Module (`/users`).

Khung endpoint theo docs/API_SPEC.md - mục 2. `GET /users`, `GET /users/{id}`,
`PUT /users/{id}/status` implement lúc port trang Quản lý người dùng Admin
(Frontend) - xem docstring `app/services/user_service.py`.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user, require_role
from app.models.user import User, UserRole
from app.schemas.common import (
    APIResponse,
    MessageResponse,
    PaginatedResponse,
    PaginationParams,
    paginated_response,
    success_response,
)
from app.schemas.user import ChangePasswordRequest, UserResponse, UserStatusUpdate, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["User"])


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy người dùng")


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
    db: Annotated[Session, Depends(get_db)],
    pagination: Annotated[PaginationParams, Depends()],
    role: UserRole | None = None,
    is_active: bool | None = None,
    # Tìm theo tên HOẶC email - cùng pattern gộp 1 ô search của
    # `GET /orders/admin` (task 4.4.2), xem user_service.list_users().
    search: str | None = None,
) -> APIResponse[PaginatedResponse[UserResponse]]:
    """Danh sách toàn bộ user (phân trang, filter role/trạng thái, tìm theo
    tên/email qua `?search=`). Yêu cầu: Admin."""
    items, total = user_service.list_users(
        db,
        page=pagination.page,
        page_size=pagination.page_size,
        role=role,
        is_active=is_active,
        search=search,
    )
    return success_response(data=paginated_response(items, total, pagination.page, pagination.page_size))


@router.get(
    "/{user_id}",
    response_model=APIResponse[UserResponse],
    summary="Xem chi tiết 1 user",
    responses=auth_responses(forbidden=True, not_found=True),
)
def get_user(
    user_id: int,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
) -> APIResponse[UserResponse]:
    """Xem chi tiết 1 user. Yêu cầu: Admin."""
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise _not_found()
    return success_response(data=UserResponse.model_validate(user))


@router.put(
    "/{user_id}/status",
    response_model=APIResponse[UserResponse],
    summary="Khóa/mở khóa tài khoản user",
    responses=auth_responses(forbidden=True, not_found=True),
)
def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[Session, Depends(get_db)],
) -> APIResponse[UserResponse]:
    """Khóa/mở khóa tài khoản user. Yêu cầu: Admin."""
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise _not_found()
    user_service.update_user_status(db, user, payload.is_active)
    return success_response(
        data=UserResponse.model_validate(user),
        message="Đã mở khóa tài khoản" if payload.is_active else "Đã khóa tài khoản",
    )
