from __future__ import annotations

from datetime import date

from sqlalchemy import Boolean, Enum as SQLEnum, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db_config import Base
from db.models.enums import (
    DayOfWeekEnum,
    FatigueStatusEnum,
    PerceivedDifficultyEnum,
    SatisfactionEnum,
    SlotTypeEnum,
    WorkoutStatusEnum,
    enum_values,
)


class WorkoutStandard(Base):
    __tablename__ = "workout_standard"

    workout_standard_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    standard_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    workout_plans: Mapped[list[WorkoutPlan]] = relationship(
        "WorkoutPlan",
        back_populates="workout_standard",
    )


class WorkoutPlan(Base):
    __tablename__ = "workout_plan"

    workout_plan_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    workout_standard_id: Mapped[int] = mapped_column(
        ForeignKey("workout_standard.workout_standard_id", ondelete="RESTRICT"),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(nullable=False)
    workout_status: Mapped[WorkoutStatusEnum] = mapped_column(
        SQLEnum(WorkoutStatusEnum, name="workout_status_enum", values_callable=enum_values),
        nullable=False,
    )
    satisfaction: Mapped[SatisfactionEnum | None] = mapped_column(
        SQLEnum(SatisfactionEnum, name="satisfaction_enum", values_callable=enum_values),
    )

    student: Mapped[Student] = relationship(
        "Student",
        back_populates="workout_plans",
    )
    workout_standard: Mapped[WorkoutStandard] = relationship(
        "WorkoutStandard",
        back_populates="workout_plans",
    )
    assigned_exercises: Mapped[list[AssignedExercise]] = relationship(
        "AssignedExercise",
        back_populates="workout_plan",
    )
    assigned_exercise_interactions: Mapped[list[StudentAssignedExerciseInteraction]] = relationship(
        "StudentAssignedExerciseInteraction",
        back_populates="workout_plan",
    )
    muscle_fatigue: Mapped[list[MuscleFatigue]] = relationship(
        "MuscleFatigue",
        back_populates="workout_plan",
    )


class AssignedExercise(Base):
    __tablename__ = "assigned_exercise"

    assigned_exercise_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workout_plan_id: Mapped[int] = mapped_column(
        ForeignKey("workout_plan.workout_plan_id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.exercise_id", ondelete="RESTRICT"),
        nullable=False,
    )
    slot_type: Mapped[SlotTypeEnum] = mapped_column(
        SQLEnum(SlotTypeEnum, name="slot_type_enum", values_callable=enum_values),
        nullable=False,
    )
    day_of_week: Mapped[DayOfWeekEnum] = mapped_column(
        SQLEnum(DayOfWeekEnum, name="day_of_week_enum", values_callable=enum_values),
        nullable=False,
    )
    order_in_session: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_score: Mapped[float | None] = mapped_column(Float)
    recommended_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_reps: Mapped[int] = mapped_column(Integer, nullable=False)

    workout_plan: Mapped[WorkoutPlan] = relationship(
        "WorkoutPlan",
        back_populates="assigned_exercises",
    )
    exercise: Mapped[Exercise] = relationship(
        "Exercise",
        back_populates="assigned_exercises",
    )
    muscle_groups: Mapped[list[AssignedExerciseMuscleGroup]] = relationship(
        "AssignedExerciseMuscleGroup",
        back_populates="assigned_exercise",
    )
    interactions: Mapped[list[StudentAssignedExerciseInteraction]] = relationship(
        "StudentAssignedExerciseInteraction",
        back_populates="assigned_exercise",
    )
    muscle_fatigue: Mapped[list[MuscleFatigue]] = relationship(
        "MuscleFatigue",
        back_populates="assigned_exercise",
    )


class StudentAssignedExerciseInteraction(Base):
    __tablename__ = "student_assigned_exercise_interaction"

    assigned_exercise_interaction_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    workout_plan_id: Mapped[int] = mapped_column(
        ForeignKey("workout_plan.workout_plan_id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("assigned_exercise.assigned_exercise_id", ondelete="CASCADE"),
        nullable=False,
    )
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actually_sets: Mapped[int | None] = mapped_column(Integer)
    actually_reps: Mapped[int | None] = mapped_column(Integer)
    perceived_difficulty: Mapped[PerceivedDifficultyEnum | None] = mapped_column(
        SQLEnum(
            PerceivedDifficultyEnum,
            name="perceived_difficulty_enum",
            values_callable=enum_values,
        ),
    )
    feedback_notes: Mapped[str | None] = mapped_column(Text)
    interaction_date: Mapped[date] = mapped_column(nullable=False)
    exercise_status: Mapped[WorkoutStatusEnum] = mapped_column(
        SQLEnum(WorkoutStatusEnum, name="exercise_status_enum", values_callable=enum_values),
        nullable=False,
    )

    student: Mapped[Student] = relationship(
        "Student",
        back_populates="assigned_exercise_interactions",
    )
    workout_plan: Mapped[WorkoutPlan] = relationship(
        "WorkoutPlan",
        back_populates="assigned_exercise_interactions",
    )
    assigned_exercise: Mapped[AssignedExercise] = relationship(
        "AssignedExercise",
        back_populates="interactions",
    )


class AssignedExerciseMuscleGroup(Base):
    __tablename__ = "assigned_exercise_muscle_group"

    assigned_exercise_muscle_group_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assigned_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("assigned_exercise.assigned_exercise_id", ondelete="CASCADE"),
        nullable=False,
    )
    muscle_group_id: Mapped[int] = mapped_column(
        ForeignKey("muscle_group.muscle_group_id", ondelete="RESTRICT"),
        nullable=False,
    )

    assigned_exercise: Mapped[AssignedExercise] = relationship(
        "AssignedExercise",
        back_populates="muscle_groups",
    )
    muscle_group: Mapped[MuscleGroup] = relationship(
        "MuscleGroup",
        back_populates="assigned_exercise_links",
    )
    muscle_fatigue: Mapped[list[MuscleFatigue]] = relationship(
        "MuscleFatigue",
        back_populates="assigned_exercise_muscle_group",
    )


class MuscleFatigue(Base):
    __tablename__ = "muscle_fatigue"

    muscle_fatigue_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workout_plan_id: Mapped[int] = mapped_column(
        ForeignKey("workout_plan.workout_plan_id", ondelete="CASCADE"),
        nullable=False,
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_exercise_id: Mapped[int] = mapped_column(
        ForeignKey("assigned_exercise.assigned_exercise_id", ondelete="CASCADE"),
        nullable=False,
    )
    assigned_exercise_muscle_group_id: Mapped[int] = mapped_column(
        ForeignKey(
            "assigned_exercise_muscle_group.assigned_exercise_muscle_group_id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    date: Mapped[date] = mapped_column(nullable=False)
    recovery_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[FatigueStatusEnum] = mapped_column(
        SQLEnum(FatigueStatusEnum, name="fatigue_status_enum", values_callable=enum_values),
        nullable=False,
    )
    recovery_left: Mapped[int] = mapped_column(Integer, nullable=False)

    workout_plan: Mapped[WorkoutPlan] = relationship(
        "WorkoutPlan",
        back_populates="muscle_fatigue",
    )
    student: Mapped[Student] = relationship(
        "Student",
        back_populates="muscle_fatigue",
    )
    assigned_exercise: Mapped[AssignedExercise] = relationship(
        "AssignedExercise",
        back_populates="muscle_fatigue",
    )
    assigned_exercise_muscle_group: Mapped[AssignedExerciseMuscleGroup] = relationship(
        "AssignedExerciseMuscleGroup",
        back_populates="muscle_fatigue",
    )
