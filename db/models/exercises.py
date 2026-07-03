from __future__ import annotations

from datetime import date

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.db_config import Base


class ExerciseCategory(Base):
    __tablename__ = "exercise_categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_name: Mapped[str] = mapped_column(String, nullable=False)

    exercises: Mapped[list[Exercise]] = relationship(
        "Exercise",
        back_populates="category",
    )


class MuscleGroup(Base):
    __tablename__ = "muscle_group"

    muscle_group_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    muscle_name: Mapped[str] = mapped_column(String, nullable=False)

    exercise_links: Mapped[list[JTExerciseMuscleGroup]] = relationship(
        "JTExerciseMuscleGroup",
        back_populates="muscle_group",
    )
    assigned_exercise_links: Mapped[list[AssignedExerciseMuscleGroup]] = relationship(
        "AssignedExerciseMuscleGroup",
        back_populates="muscle_group",
    )


class Equipment(Base):
    __tablename__ = "equipment"

    equipment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipment_name: Mapped[str] = mapped_column(String, nullable=False)

    exercise_links: Mapped[list[JTExerciseEquipment]] = relationship(
        "JTExerciseEquipment",
        back_populates="equipment",
    )


class InjuryType(Base):
    __tablename__ = "injury_types"

    injury_type_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type_name: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    body_region: Mapped[str] = mapped_column(String, nullable=False)
    severity_class: Mapped[str] = mapped_column(String, nullable=False)
    typical_recovery_weeks: Mapped[int] = mapped_column(Integer, nullable=False)

    student_history: Mapped[list[StudentInjuryHistory]] = relationship(
        "StudentInjuryHistory",
        back_populates="injury_type",
    )
    exercise_contraindications: Mapped[list[JTExerciseContraindication]] = relationship(
        "JTExerciseContraindication",
        back_populates="injury_type",
    )


class Exercise(Base):
    __tablename__ = "exercises"

    exercise_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exercise_name: Mapped[str] = mapped_column(String, nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("exercise_categories.category_id", ondelete="RESTRICT"),
        nullable=False,
    )
    difficulty: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    recommended_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_reps: Mapped[int] = mapped_column(Integer, nullable=False)
    rest_between_sets_sec: Mapped[int] = mapped_column(Integer, nullable=False)

    category: Mapped[ExerciseCategory] = relationship(
        "ExerciseCategory",
        back_populates="exercises",
    )
    muscle_groups: Mapped[list[JTExerciseMuscleGroup]] = relationship(
        "JTExerciseMuscleGroup",
        back_populates="exercise",
    )
    equipment: Mapped[list[JTExerciseEquipment]] = relationship(
        "JTExerciseEquipment",
        back_populates="exercise",
    )
    contraindications: Mapped[list[JTExerciseContraindication]] = relationship(
        "JTExerciseContraindication",
        back_populates="exercise",
    )
    assigned_exercises: Mapped[list[AssignedExercise]] = relationship(
        "AssignedExercise",
        back_populates="exercise",
    )


class JTExerciseMuscleGroup(Base):
    __tablename__ = "exercise_muscle_group"

    exercise_muscle_group_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.exercise_id", ondelete="CASCADE"),
        nullable=False,
    )
    muscle_group_id: Mapped[int] = mapped_column(
        ForeignKey("muscle_group.muscle_group_id", ondelete="RESTRICT"),
        nullable=False,
    )

    exercise: Mapped[Exercise] = relationship(
        "Exercise",
        back_populates="muscle_groups",
    )
    muscle_group: Mapped[MuscleGroup] = relationship(
        "MuscleGroup",
        back_populates="exercise_links",
    )


class JTExerciseEquipment(Base):
    __tablename__ = "exercise_equipment"

    exercise_equipment_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.exercise_id", ondelete="CASCADE"),
        nullable=False,
    )
    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.equipment_id", ondelete="RESTRICT"),
        nullable=False,
    )

    exercise: Mapped[Exercise] = relationship(
        "Exercise",
        back_populates="equipment",
    )
    equipment: Mapped[Equipment] = relationship(
        "Equipment",
        back_populates="exercise_links",
    )


class JTExerciseContraindication(Base):
    __tablename__ = "exercise_contraindications"

    exercise_contraindication_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exercise_id: Mapped[int] = mapped_column(
        ForeignKey("exercises.exercise_id", ondelete="CASCADE"),
        nullable=False,
    )
    injury_type_id: Mapped[int] = mapped_column(
        ForeignKey("injury_types.injury_type_id", ondelete="RESTRICT"),
        nullable=False,
    )

    exercise: Mapped[Exercise] = relationship(
        "Exercise",
        back_populates="contraindications",
    )
    injury_type: Mapped[InjuryType] = relationship(
        "InjuryType",
        back_populates="exercise_contraindications",
    )


class StudentInjuryHistory(Base):
    __tablename__ = "student_injury_history"

    injury_record_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.student_id", ondelete="CASCADE"),
        nullable=False,
    )
    injury_type_id: Mapped[int] = mapped_column(
        ForeignKey("injury_types.injury_type_id", ondelete="RESTRICT"),
        nullable=False,
    )
    diagnosis_date: Mapped[date] = mapped_column(nullable=False)
    recovery_date: Mapped[date | None] = mapped_column()
    recovery_status: Mapped[str] = mapped_column(String, nullable=False)
    doctor_notes: Mapped[str | None] = mapped_column(Text)

    student: Mapped[Student] = relationship(
        "Student",
        back_populates="injury_history",
    )
    injury_type: Mapped[InjuryType] = relationship(
        "InjuryType",
        back_populates="student_history",
    )
