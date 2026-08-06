"""Router: Auth Module (`/auth`).

Khung endpoint theo docs/API_SPEC.md - mục 1. Logic thật (hash password, JWT,
Redis blacklist...) sẽ implement ở task 1.3.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.openapi_responses import auth_responses
from app.core.security import create_access_token, create_refresh_token, get_current_user
from app.models.user import User
from app.schemas.common import APIResponse, MessageResponse, success_response
from app.schemas.user import RefreshTokenRequest, TokenPair, UserCreate, UserLogin, UserResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=APIResponse[UserResponse],
    summary="Đăng ký tài khoản Customer",
    status_code=status.HTTP_201_CREATED,
    responses={400: {"description": "Email đã được đăng ký"}},
)
def register(payload: UserCreate, db: Annotated[Session, Depends(get_db)]) -> APIResponse[UserResponse]:
    """Đăng ký tài khoản Customer. Public.

    Role luôn được gán "customer" ở tầng service - client không thể tự đăng ký
    admin (UserCreate không có field role, đúng ràng buộc trong docs/DATABASE_SCHEMA.md).
    """
    if auth_service.get_user_by_email(db, payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email đã được đăng ký")
    user = auth_service.register_user(db, payload)
    return APIResponse(data=UserResponse.model_validate(user), message="Đăng ký thành công")


@router.post(
    "/login",
    response_model=APIResponse[TokenPair],
    summary="Đăng nhập",
    responses={
        401: {"description": "Email hoặc mật khẩu không đúng"},
        403: {"description": "Tài khoản đã bị khóa"},
    },
)
def login(payload: UserLogin, db: Annotated[Session, Depends(get_db)]) -> APIResponse[TokenPair]:
    """Đăng nhập, trả về access token + refresh token. Public."""
    user = auth_service.authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email hoặc mật khẩu không đúng")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tài khoản đã bị khóa")

    access_token = create_access_token(user_id=user.id, role=user.role.value)
    refresh_token = create_refresh_token(user_id=user.id)
    return APIResponse(
        data=TokenPair(access_token=access_token, refresh_token=refresh_token),
        message="Đăng nhập thành công",
    )


@router.post(
    "/refresh",
    response_model=APIResponse[TokenPair],
    summary="Làm mới access token",
)
def refresh(payload: RefreshTokenRequest) -> APIResponse[TokenPair]:
    """Làm mới access token bằng refresh token. Public."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 1.3")


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Đăng xuất",
    responses=auth_responses(),
)
def logout(current_user: Annotated[User, Depends(get_current_user)]) -> MessageResponse:
    """Đăng xuất, đưa refresh token vào Redis blacklist. Yêu cầu: Customer, Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 1.3")


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Lấy thông tin user hiện tại",
    responses=auth_responses(),
)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> APIResponse[UserResponse]:
    """Lấy thông tin user hiện tại từ token. Yêu cầu: Customer, Admin.

    Cùng logic với GET /users/me (app/routers/user.py) - current_user đã là
    chính user cần trả về (get_current_user load từ DB rồi), không cần query
    thêm. Cần thiết cho luồng Frontend: /auth/login chỉ trả TokenPair (không
    có role), Frontend gọi endpoint này ngay sau khi có token để biết role
    thật rồi mới redirect đúng (task 2.3.4, xem docs/KNOWN_TODOS.md #9).
    """
    return success_response(data=UserResponse.model_validate(current_user))
