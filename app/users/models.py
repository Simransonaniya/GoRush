from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.common.enums.chat import UserRole
from app.database.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.database.session import Base


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    external_ref: Mapped[str] = mapped_column(String(128), unique=True, index=True)  # GoRush user id
    role: Mapped[UserRole] = mapped_column(String(32), index=True)
    phone_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)  # never store raw phone
    preferred_language: Mapped[str] = mapped_column(String(16), default="en")
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(default=True)
