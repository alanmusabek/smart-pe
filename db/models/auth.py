from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db_config import Base
from db.models.enums import UserRoleEnum, enum_values


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRoleEnum] = mapped_column(
        SQLEnum(UserRoleEnum, name="user_role_enum", values_callable=enum_values),
        nullable=False,
    )
    student_id: Mapped[int | None] = mapped_column(
        ForeignKey("students.student_id", ondelete="SET NULL"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    student: Mapped[Student | None] = relationship(
        "Student",
        back_populates="users",
    )
    attendance_sessions: Mapped[list[AttendanceSession]] = relationship(
        "AttendanceSession",
        back_populates="teacher_user",
    )
