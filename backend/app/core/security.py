"""Xác thực JWT (placeholder cho task 1.2.2 - Swagger docs).

`get_current_user` hiện tại CHỈ kiểm tra có Bearer token trong header hay không
(401 nếu thiếu) - đủ để đánh dấu đúng endpoint nào cần đăng nhập trên Swagger UI
và để "Try it out" chạy được sau khi bấm Authorize. Việc decode JWT thật, load
user từ MySQL, và kiểm tra role (Customer/Admin) sẽ implement ở task 1.3.3.
"""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# tokenUrl chỉ dùng để Swagger UI biết endpoint lấy token khi bấm nút "Authorize".
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


def get_current_user(token: Annotated[str | None, Depends(oauth2_scheme)]) -> dict[str, Any]:
    """Dependency PLACEHOLDER cho các route yêu cầu đăng nhập.

    TODO (task 1.3.3): decode JWT thật bằng python-jose + settings.JWT_SECRET_KEY,
    load user từ MySQL, kiểm tra role tương ứng với từng endpoint (Customer/Admin).
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"id": "placeholder-user-id", "role": "customer"}
