"""Pydantic schemas: Auth / User (request & response models).

Khớp với bảng `users` trong docs/DATABASE_SCHEMA.md (task 1.3.1).
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole
from app.schemas.base import BaseSchema


class UserCreate(BaseModel):
    """Payload đăng ký tài khoản (task 1.3.2).

    Chứa `password` dạng plain text (client gửi lên) - KHÔNG chứa `password_hash`,
    việc hash mật khẩu (passlib) thực hiện ở service layer trước khi lưu DB.
    """

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)


class UserResponse(BaseSchema):
    """Response trả về API - LOẠI TRỪ `password_hash`."""

    id: int
    email: EmailStr
    full_name: str
    phone: str | None = None
    address: str | None = None
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    """Cập nhật thông tin cá nhân - toàn bộ field optional."""

    full_name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, max_length=20)
    address: str | None = Field(default=None, max_length=500)


# ---- Các schema khác cho module Auth/User (task 1.2.2 - Swagger, 1.3.2 - Auth) ----


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


class UserStatusUpdate(BaseModel):
    is_active: bool
