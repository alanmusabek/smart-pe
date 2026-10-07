from __future__ import annotations

from datetime import date

from sqlalchemy import CheckConstraint, Enum as SQLEnum, Float, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db_config import Base
from db.models.enums import CreditStatusEnum, GenderEnum, TestTypeEnum, enum_values


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("age BETWEEN 16 AND 30", name="ck_students_age"),
    )

    student_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_name: Mapped[str] = mapped_column(String, nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[GenderEnum] = mapped_column(
        SQLEnum(GenderEnum, name="gender_enum", values_callable=enum_values),
        nullable=False,
    )

    health_profiles: Mapped[list[StudentsHealthProfile]] = relationship(
        "StudentsHealthProfile",
        back_populates="student",
    )
    injury_history: Mapped[list[StudentInjuryHistory]] = relationship(
        "StudentInjuryHistory",
        back_populates="student",
    )
    workout_plans: Mapped[list[WorkoutPlan]] = relationship(
        "WorkoutPlan",
        back_populates="student",
    )
    assigned_exercise_interactions: Mapped[list[StudentAssignedExerciseInteraction]] = relationship(
        "StudentAssignedExerciseInteraction",
        back_populates="student",
    )
    muscle_fatigue: Mapped[list[MuscleFatigue]] = relationship(
        "MuscleFatigue",
        back_populates="student",
    )
    users: Mapped[list[User]] = relationship(
        "User",
        back_populates="student",
    )
    daily_activities: Mapped[list[DailyActivity]] = relationship(
        "DailyActivity",
        back_populates="student",
    )
    attendance_records: Mapped[list[AttendanceRecord]] = relationship(
        "AttendanceRecord",
        back_populates="student",
    )
    test_attempts: Mapped[list[StudentTestAttempt]] = relationship(
        "StudentTestAttempt",
        back_populates="student",
    )
    achievements: Mapped[list[StudentAchievement]] = relationship(
        "StudentAchievement",
        back_populates="student",
    )
    rating_snapshots: Mapped[list[StudentRatingSnapshot]] = relationship(
        "StudentRatingSnapshot",
        back_populates="student",
    )
    credit_statuses: Mapped[list[StudentCreditStatus]] = relationship(
        "StudentCreditStatus",
        back_populates="student",
    )


class MedicalGroup(Base):
    __tablename__ = "medical_group"

    group_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    health_profiles: Mapped[list[StudentsHealthProfile]] = relationship(
        "StudentsHealthProfile",
        back_populates="medical_group",
    )
    assessment_rules: Mapped[list[AssessmentRule]] = relationship(
        "AssessmentRule",
        back_populates="medical_group",
    )


class StudentsHealthProfile(Base):
    __tablename__ = "students_health_profiles"

    health_profile_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    medical_group_id: Mapped[int] = mapped_column(
        ForeignKey("medical_group.group_id", ondelete="RESTRICT"),
        nullable=False,
    )
    height_cm: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    cooper_meters: Mapped[float] = mapped_column(Float, nullable=False)
    jump_forward: Mapped[float] = mapped_column(Float, nullable=False)
    flexibility_cm: Mapped[float] = mapped_column(Float, nullable=False)
    push_ups: Mapped[int] = mapped_column(Integer, nullable=False)
    pull_ups: Mapped[int] = mapped_column(Integer, nullable=False)
    sit_ups: Mapped[int] = mapped_column(Integer, nullable=False)
    measurement_date: Mapped[date] = mapped_column(nullable=False)

    student: Mapped[Student] = relationship(
        "Student",
        back_populates="health_profiles",
    )
    medical_group: Mapped[MedicalGroup] = relationship(
        "MedicalGroup",
        back_populates="health_profiles",
    )
    physical_readiness_assessments: Mapped[list[StudentsPhysicalReadinessAssessment]] = relationship(
        "StudentsPhysicalReadinessAssessment",
        back_populates="health_profile",
    )


class AssessmentVersion(Base):
    __tablename__ = "assessment_version"

    assessment_version_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    effective_date: Mapped[date] = mapped_column(nullable=False)

    assessment_rules: Mapped[list[AssessmentRule]] = relationship(
        "AssessmentRule",
        back_populates="assessment_version",
    )
    physical_readiness_assessments: Mapped[list[StudentsPhysicalReadinessAssessment]] = relationship(
        "StudentsPhysicalReadinessAssessment",
        back_populates="assessment_version",
    )


class AssessmentRule(Base):
    __tablename__ = "assessment_rule"
    __table_args__ = (
        CheckConstraint("score BETWEEN 1 AND 4", name="ck_assessment_rule_score"),
        CheckConstraint("min_value <= max_value", name="ck_assessment_rule_min_value_lte_max_value"),
    )

    rule_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_version_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_version.assessment_version_id", ondelete="CASCADE"),
        nullable=False,
    )
    medical_group_id: Mapped[int] = mapped_column(
        ForeignKey("medical_group.group_id", ondelete="RESTRICT"),
        nullable=False,
    )
    test_type: Mapped[TestTypeEnum] = mapped_column(
        SQLEnum(TestTypeEnum, name="test_type_enum", values_callable=enum_values),
        nullable=False,
    )
    gender: Mapped[GenderEnum] = mapped_column(
        SQLEnum(GenderEnum, name="gender_enum", values_callable=enum_values),
        nullable=False,
    )
    min_value: Mapped[float] = mapped_column(Float, nullable=False)
    max_value: Mapped[float] = mapped_column(Float, nullable=False)
    score: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    assessment_version: Mapped[AssessmentVersion] = relationship(
        "AssessmentVersion",
        back_populates="assessment_rules",
    )
    medical_group: Mapped[MedicalGroup] = relationship(
        "MedicalGroup",
        back_populates="assessment_rules",
    )


class StudentsPhysicalReadinessAssessment(Base):
    __tablename__ = "students_physical_readiness_assessments"

    evaluation_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    health_profile_id: Mapped[int] = mapped_column(
        ForeignKey("students_health_profiles.health_profile_id", ondelete="CASCADE"),
        nullable=False,
    )
    assessment_version_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_version.assessment_version_id", ondelete="RESTRICT"),
        nullable=False,
    )
    BMI: Mapped[float] = mapped_column(Float, nullable=False)
    strength_score: Mapped[float] = mapped_column(Float, nullable=False)
    endurance_score: Mapped[float] = mapped_column(Float, nullable=False)
    flexibility_score: Mapped[float] = mapped_column(Float, nullable=False)

    health_profile: Mapped[StudentsHealthProfile] = relationship(
        "StudentsHealthProfile",
        back_populates="physical_readiness_assessments",
    )
    assessment_version: Mapped[AssessmentVersion] = relationship(
        "AssessmentVersion",
        back_populates="physical_readiness_assessments",
    )


class StudentCreditStatus(Base):
    __tablename__ = "student_credit_status"

    credit_status_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    assessment_version_id: Mapped[int] = mapped_column(
        ForeignKey("assessment_version.assessment_version_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[CreditStatusEnum] = mapped_column(
        SQLEnum(CreditStatusEnum, name="credit_status_enum", values_callable=enum_values),
        nullable=False,
    )
    updated_at: Mapped[date] = mapped_column(nullable=False)

    student: Mapped[Student] = relationship(
        "Student",
        back_populates="credit_statuses",
    )
    assessment_version: Mapped[AssessmentVersion] = relationship(
        "AssessmentVersion",
    )
