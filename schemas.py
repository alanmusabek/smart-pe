from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime

class PlanRequest(BaseModel):
    student_id: int
    save_to_db: bool = True

class InteractionUpdate(BaseModel):
    assigned_exercise_id: int
    completed: bool
    actually_sets: Optional[int] = None
    actually_reps: Optional[int] = None
    actually_weight: Optional[float] = Field(None, description="Weight used in kg")
    perceived_difficulty: Optional[str] = Field(
        None, description="Very Easy | Easy | Normal | Hard | Very Hard"
    )
    feedback_notes: Optional[str] = None
    exercise_status: str = Field(
        "COMPLETED", description="COMPLETED | SKIPPED | DISCARDED | IN_PROGRESS"
    )

class InteractionEdit(BaseModel):
    completed: Optional[bool] = None
    actually_sets: Optional[int] = None
    actually_reps: Optional[int] = None
    actually_weight: Optional[float] = None
    perceived_difficulty: Optional[str] = None
    exercise_status: Optional[str] = None
    feedback_notes: Optional[str] = None
    
class PlanStatusUpdate(BaseModel):
    workout_plan_id: int
    workout_status: str = Field(description="COMPLETED | DISCARDED | SKIPPED | IN_PROGRESS")
    satisfaction: Optional[str] = Field(None, description="Liked | Disliked")
    feedback_notes: Optional[str] = None

class RetrainRequest(BaseModel):
    force: bool = False

class HealthProfileUpdate(BaseModel):
    medical_group_id: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    cooper_meters: Optional[int] = None
    push_ups: Optional[int] = None
    pull_ups: Optional[int] = None
    flexibility_cm: Optional[float] = None
    sit_ups: Optional[int] = None
    jump_forward: Optional[int] = None

class InjuryCreate(BaseModel):
    injury_type_id: int
    diagnosis_date: date
    recovery_date: Optional[date] = None
    recovery_status: str = "active"

class InjuryUpdate(BaseModel):
    injury_type_id: Optional[int] = None
    diagnosis_date: Optional[date] = None
    recovery_date: Optional[date] = None
    recovery_status: Optional[str] = None

class MuscleFatigueUpdate(BaseModel):
    status: Optional[str] = None  # "ACTIVE" or "NOT ACTIVE"
    recovery_left: Optional[float] = None

class ExerciseUpdate(BaseModel):
    exercise_id: Optional[int] = None
    recommended_sets: Optional[int] = None
    recommended_reps: Optional[int] = None
    slot_type: Optional[str] = None
    day_of_week: Optional[str] = None
    order_in_session: Optional[int] = None

class ExerciseCreate(BaseModel):
    exercise_id: int
    slot_type: str
    day_of_week: str
    order_in_session: int
    recommended_sets: int
    recommended_reps: int

class WorkoutFeedback(BaseModel):
    workout_plan_id: int
    satisfaction: str = Field(description="Liked | Disliked | Neutral")
    feedback_notes: Optional[str] = None
    difficulty_rating: Optional[int] = Field(None, ge=1, le=5, description="1=Very Easy, 5=Very Hard")

class QRAttendance(BaseModel):
    student_id: int
    class_id: int
    qr_code: str
