"""Router: Auth Module (`/auth`).

Khung endpoint theo docs/API_SPEC.md - mục 1. Logic thật (hash password, JWT,
Redis blacklist...) sẽ implement ở task 1.3.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.openapi_responses import auth_responses
from app.core.security import get_current_user
from app.schemas.common import APIResponse, MessageResponse
from app.schemas.user import RefreshTokenRequest, TokenPair, UserCreate, UserLogin, UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=APIResponse[UserResponse],
    summary="Đăng ký tài khoản Customer",
    status_code=status.HTTP_201_CREATED,
)
def register(payload: UserCreate) -> APIResponse[UserResponse]:
    """Đăng ký tài khoản Customer. Public."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 1.3")


@router.post(
    "/login",
    response_model=APIResponse[TokenPair],
    summary="Đăng nhập",
)
def login(payload: UserLogin) -> APIResponse[TokenPair]:
    """Đăng nhập, trả về access token + refresh token. Public."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 1.3")


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
def logout(current_user: Annotated[dict, Depends(get_current_user)]) -> MessageResponse:
    """Đăng xuất, đưa refresh token vào Redis blacklist. Yêu cầu: Customer, Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 1.3")


@router.get(
    "/me",
    response_model=APIResponse[UserResponse],
    summary="Lấy thông tin user hiện tại",
    responses=auth_responses(),
)
def get_me(current_user: Annotated[dict, Depends(get_current_user)]) -> APIResponse[UserResponse]:
    """Lấy thông tin user hiện tại từ token. Yêu cầu: Customer, Admin."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Chưa triển khai - task 1.3")
