"""Router: Auth (đăng ký, đăng nhập, JWT).

TODO (Thành viên A): thêm các endpoint /register, /login, /refresh, /me...
Sử dụng app.services.auth_service + app.schemas.user cho logic thực tế.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Route kiểm tra router Auth đã được include đúng."""
    return {"module": "auth", "status": "ok"}
