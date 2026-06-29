"""
Repository package initialization.
"""

from .student_repo import (
    get_student_profile,
    get_student_stats,
    get_student_preferences,
    update_student_last_interaction,
    get_interaction_history,
)
from .workout_repo import (
    get_latest_plan,
    get_plan_exercises,
    create_workout_plan,
    get_workout_history,
    log_workout_completion,
    get_exercise_by_name,
)
from .fatigue_repo import (
    get_muscle_fatigue,
    get_fatigue_history,
    calculate_recovery_score,
    update_fatigue_after_workout,
    get_rest_recommendations,
)

__all__ = [
    # Student
    "get_student_profile",
    "get_student_stats",
    "get_student_preferences",
    "update_student_last_interaction",
    "get_interaction_history",
    # Workout
    "get_latest_plan",
    "get_plan_exercises",
    "create_workout_plan",
    "get_workout_history",
    "log_workout_completion",
    "get_exercise_by_name",
    # Fatigue
    "get_muscle_fatigue",
    "get_fatigue_history",
    "calculate_recovery_score",
    "update_fatigue_after_workout",
    "get_rest_recommendations",
]
