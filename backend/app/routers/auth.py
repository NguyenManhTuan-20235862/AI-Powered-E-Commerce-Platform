"""Router: Auth Module (`/auth`).

Khung endpoint theo docs/API_SPEC.md - mục 1. Logic thật (hash password, JWT,
Redis blacklist...) sẽ implement ở task 1.3.
"""

from typing import Annotated

import redis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db, get_redis
from app.core.openapi_responses import auth_responses
from app.core.security import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_token_payload,
    get_user_from_refresh_token,
    try_decode_token,
)
from app.models.user import User
from app.schemas.common import APIResponse, MessageResponse, success_response
from app.schemas.user import LogoutRequest, RefreshTokenRequest, TokenPair, UserCreate, UserLogin, UserResponse
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
    responses=auth_responses(),
)
def refresh(
    payload: RefreshTokenRequest,
    db: Annotated[Session, Depends(get_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> APIResponse[TokenPair]:
    """Làm mới access token bằng refresh token. Public (chính refresh token
    trong body mới là thứ xác thực request này, không phải `Authorization`
    header).

    KHÔNG xoay vòng (rotate) refresh token - chỉ cấp access token MỚI, trả lại
    NGUYÊN refresh token client đã gửi lên (quyết định đã xác nhận: đơn giản
    hơn, khớp mức độ phức tạp hiện tại của dự án - refresh token vẫn dùng lại
    được tới khi tự hết hạn hoặc bị revoke lúc logout, xem `POST /auth/logout`).
    """
    user = get_user_from_refresh_token(db, redis_client, payload.refresh_token)
    access_token = create_access_token(user_id=user.id, role=user.role.value)
    return APIResponse(
        data=TokenPair(access_token=access_token, refresh_token=payload.refresh_token),
        message="Làm mới access token thành công",
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Đăng xuất",
    responses=auth_responses(),
)
def logout(
    # current_user: chỉ dùng làm cổng xác thực (401 nếu token đã hết hạn/sai/
    # đã bị blacklist từ trước) - handler không cần current_user.id.
    current_user: Annotated[User, Depends(get_current_user)],
    token_payload: Annotated[dict, Depends(get_token_payload)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
    payload: LogoutRequest | None = None,
) -> MessageResponse:
    """Đăng xuất - đưa ACCESS token đang dùng vào Redis blacklist (task 3.3.2),
    VÀ đưa LUÔN refresh token vào blacklist nếu client gửi kèm trong body
    (`LogoutRequest.refresh_token`, optional - đúng docs/API_SPEC.md "đưa
    refresh token vào Redis blacklist"). Refresh token sai/hết hạn/thiếu
    trong body KHÔNG làm logout thất bại - best-effort, access token blacklist
    (xác thực bằng `Authorization` header) mới là phần bắt buộc.

    Yêu cầu: Customer, Admin.
    """
    blacklist_token(redis_client, token_payload)

    if payload and payload.refresh_token:
        refresh_payload = try_decode_token(payload.refresh_token)
        if refresh_payload and refresh_payload.get("type") == "refresh":
            blacklist_token(redis_client, refresh_payload)

    return MessageResponse(message="Đăng xuất thành công")


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
