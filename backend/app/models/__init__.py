"""Import toàn bộ model ở đây để Base.metadata luôn đầy đủ khi Alembic autogenerate."""

from app.models.user import User, UserRole

__all__ = ["User", "UserRole"]
