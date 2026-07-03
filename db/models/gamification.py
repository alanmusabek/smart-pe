from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db_config import Base


class Achievement(Base):
    __tablename__ = "achievement"

    achievement_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    achievement_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    points: Mapped[int] = mapped_column(Integer, nullable=False)

    student_links: Mapped[list[StudentAchievement]] = relationship(
        "StudentAchievement",
        back_populates="achievement",
    )


class StudentAchievement(Base):
    __tablename__ = "student_achievement"

    student_achievement_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievement.achievement_id", ondelete="CASCADE"),
        nullable=False,
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    student: Mapped[Student] = relationship(
        "Student",
        back_populates="achievements",
    )
    achievement: Mapped[Achievement] = relationship(
        "Achievement",
        back_populates="student_links",
    )


class StudentRatingSnapshot(Base):
    __tablename__ = "student_rating_snapshot"

    rating_snapshot_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    points: Mapped[int] = mapped_column(Integer, nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    student: Mapped[Student] = relationship(
        "Student",
        back_populates="rating_snapshots",
    )
