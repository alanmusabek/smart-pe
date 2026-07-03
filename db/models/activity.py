from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db_config import Base


class DailyActivity(Base):
    __tablename__ = "daily_activity"

    activity_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(nullable=False)
    steps: Mapped[int] = mapped_column(Integer, nullable=False)
    calories_kcal: Mapped[float] = mapped_column(Float, nullable=False)
    active_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    student: Mapped[Student] = relationship(
        "Student",
        back_populates="daily_activities",
    )
