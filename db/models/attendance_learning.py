from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, Float, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db_config import Base
from db.models.enums import AttendanceStatusEnum, enum_values


class AttendanceSession(Base):
    __tablename__ = "attendance_session"

    attendance_session_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(nullable=False)
    qr_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    teacher_user: Mapped[User] = relationship(
        "User",
        back_populates="attendance_sessions",
    )
    records: Mapped[list[AttendanceRecord]] = relationship(
        "AttendanceRecord",
        back_populates="attendance_session",
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_record"

    attendance_record_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attendance_session_id: Mapped[int] = mapped_column(
        ForeignKey("attendance_session.attendance_session_id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    check_in_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    status: Mapped[AttendanceStatusEnum] = mapped_column(
        SQLEnum(AttendanceStatusEnum, name="attendance_status_enum", values_callable=enum_values),
        nullable=False,
    )

    attendance_session: Mapped[AttendanceSession] = relationship(
        "AttendanceSession",
        back_populates="records",
    )
    student: Mapped[Student] = relationship(
        "Student",
        back_populates="attendance_records",
    )


class SemesterNorm(Base):
    __tablename__ = "semester_norm"

    norm_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_version_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_version.assessment_version_id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    semester: Mapped[str] = mapped_column(String, nullable=False)
    academic_year: Mapped[str] = mapped_column(String, nullable=False)

    assessment_version: Mapped[AssessmentVersion] = relationship("AssessmentVersion")


class TheoreticalTest(Base):
    __tablename__ = "theoretical_test"

    test_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    questions: Mapped[list[TheoreticalQuestion]] = relationship(
        "TheoreticalQuestion",
        back_populates="test",
    )
    attempts: Mapped[list[StudentTestAttempt]] = relationship(
        "StudentTestAttempt",
        back_populates="test",
    )


class TheoreticalQuestion(Base):
    __tablename__ = "theoretical_question"

    question_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(
        ForeignKey("theoretical_test.test_id", ondelete="CASCADE"),
        nullable=False,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[dict] = mapped_column(JSON, nullable=False)
    correct_answer: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)

    test: Mapped[TheoreticalTest] = relationship(
        "TheoreticalTest",
        back_populates="questions",
    )


class StudentTestAttempt(Base):
    __tablename__ = "student_test_attempt"

    attempt_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    test_id: Mapped[int] = mapped_column(
        ForeignKey("theoretical_test.test_id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    student: Mapped[Student] = relationship(
        "Student",
        back_populates="test_attempts",
    )
    test: Mapped[TheoreticalTest] = relationship(
        "TheoreticalTest",
        back_populates="attempts",
    )
