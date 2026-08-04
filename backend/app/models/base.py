"""Base class dùng chung cho toàn bộ SQLAlchemy models (MySQL)."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
