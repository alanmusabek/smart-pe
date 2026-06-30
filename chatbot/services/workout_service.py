"""
Workout service for business logic.
Orchestrates workout generation, retrieval, and management.
"""

from typing import Dict, Any, List, Optional
from ..repository import (
    get_latest_plan,
    get_plan_exercises,
    create_workout_plan,
    get_workout_history,
    log_workout_completion,
    get_exercise_by_name,
)
from ..repository.student_repo import get_student_preferences


async def generate_personalized_workout(
    student_id: int,
    user_message: str,
    custom_focus: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a personalized workout plan for a student.
    
    Args:
        student_id: The student's ID
        user_message: Original user request message
        custom_focus: Optional custom focus area from user request
        
    Returns:
        Complete workout plan with exercises
    """
    # Get student preferences
    preferences = await get_student_preferences(student_id)
    
    # Determine focus areas
    focus_areas = [custom_focus] if custom_focus else preferences.get("focus_areas", ["full_body"])
    
    # Generate exercise list based on preferences and focus
    exercises = await _generate_exercise_list(
        focus_areas=focus_areas,
        equipment=preferences.get("equipment_available", []),
        duration=preferences.get("workout_duration", 60)
    )
    
    # Create the plan
    plan_name = f"Custom {', '.join(focus_areas)} Workout"
    created_plan = await create_workout_plan(
        student_id=student_id,
        name=plan_name,
        exercises=exercises,
        description=f"Personalized workout focusing on {', '.join(focus_areas)}"
    )
    
    return {
        "plan": created_plan,
        "preferences": preferences,
        "focus_areas": focus_areas
    }


async def _generate_exercise_list(
    focus_areas: List[str],
    equipment: List[str],
    duration: int
) -> List[Dict[str, Any]]:
    """
    Generate a list of exercises based on parameters.
    
    Args:
        focus_areas: List of muscle groups to target
        equipment: Available equipment
        duration: Target workout duration in minutes
        
    Returns:
        List of exercise dictionaries
    """
    # Base exercises for different focus areas
    exercise_templates = {
        "legs": [
            {"exercise_name": "Barbell Squat", "sets": 4, "reps": "8-10", "rest_seconds": 120},
            {"exercise_name": "Romanian Deadlift", "sets": 3, "reps": "10-12", "rest_seconds": 90},
            {"exercise_name": "Bulgarian Split Squat", "sets": 3, "reps": "10-12", "rest_seconds": 60},
            {"exercise_name": "Leg Press", "sets": 3, "reps": "12-15", "rest_seconds": 90},
        ],
        "back": [
            {"exercise_name": "Pull-ups", "sets": 4, "reps": "6-10", "rest_seconds": 120},
            {"exercise_name": "Barbell Row", "sets": 4, "reps": "8-10", "rest_seconds": 90},
            {"exercise_name": "Lat Pulldown", "sets": 3, "reps": "10-12", "rest_seconds": 60},
            {"exercise_name": "Face Pulls", "sets": 3, "reps": "15-20", "rest_seconds": 60},
        ],
        "chest": [
            {"exercise_name": "Barbell Bench Press", "sets": 4, "reps": "6-8", "rest_seconds": 120},
            {"exercise_name": "Incline Dumbbell Press", "sets": 3, "reps": "8-10", "rest_seconds": 90},
            {"exercise_name": "Dips", "sets": 3, "reps": "8-12", "rest_seconds": 90},
            {"exercise_name": "Cable Flyes", "sets": 3, "reps": "12-15", "rest_seconds": 60},
        ],
        "core": [
            {"exercise_name": "Plank", "sets": 3, "reps": "60 sec", "rest_seconds": 60},
            {"exercise_name": "Hanging Leg Raises", "sets": 3, "reps": "10-15", "rest_seconds": 60},
            {"exercise_name": "Russian Twists", "sets": 3, "reps": "20", "rest_seconds": 45},
            {"exercise_name": "Ab Wheel Rollouts", "sets": 3, "reps": "8-12", "rest_seconds": 60},
        ],
        "shoulders": [
            {"exercise_name": "Overhead Press", "sets": 4, "reps": "6-8", "rest_seconds": 120},
            {"exercise_name": "Lateral Raises", "sets": 3, "reps": "12-15", "rest_seconds": 60},
            {"exercise_name": "Rear Delt Flyes", "sets": 3, "reps": "15-20", "rest_seconds": 60},
            {"exercise_name": "Arnold Press", "sets": 3, "reps": "10-12", "rest_seconds": 90},
        ],
        "arms": [
            {"exercise_name": "Barbell Curls", "sets": 3, "reps": "8-10", "rest_seconds": 60},
            {"exercise_name": "Tricep Dips", "sets": 3, "reps": "8-12", "rest_seconds": 60},
            {"exercise_name": "Hammer Curls", "sets": 3, "reps": "10-12", "rest_seconds": 60},
            {"exercise_name": "Skull Crushers", "sets": 3, "reps": "10-12", "rest_seconds": 60},
        ]
    }
    
    # Select exercises based on focus areas
    selected_exercises = []
    for focus in focus_areas[:3]:  # Limit to 3 focus areas
        if focus in exercise_templates:
            exercises = exercise_templates[focus]
            # Take 2-3 exercises per focus area
            selected_exercises.extend(exercises[:3])
    
    # If no specific focus, create full body workout
    if not selected_exercises:
        selected_exercises = [
            {"exercise_name": "Barbell Squat", "sets": 4, "reps": "8-10", "rest_seconds": 120},
            {"exercise_name": "Bench Press", "sets": 4, "reps": "6-8", "rest_seconds": 120},
            {"exercise_name": "Barbell Row", "sets": 4, "reps": "8-10", "rest_seconds": 90},
            {"exercise_name": "Overhead Press", "sets": 3, "reps": "8-10", "rest_seconds": 90},
            {"exercise_name": "Plank", "sets": 3, "reps": "60 sec", "rest_seconds": 60},
        ]
    
    # Add position and notes
    for i, ex in enumerate(selected_exercises):
        ex["position"] = i + 1
        ex["notes"] = "Focus on proper form and controlled movement"
    
    # Adjust based on duration
    if duration < 45:
        selected_exercises = selected_exercises[:4]
    elif duration > 75:
        # Add accessory work
        selected_exercises.append({
            "exercise_name": "Farmer's Walk",
            "sets": 3,
            "reps": "40 meters",
            "rest_seconds": 90,
            "position": len(selected_exercises) + 1,
            "notes": "Great for grip strength and core stability"
        })
    
    return selected_exercises


async def get_current_plan_with_exercises(student_id: int) -> Optional[Dict[str, Any]]:
    """
    Get student's current plan with full exercise details.
    
    Args:
        student_id: The student's ID
        
    Returns:
        Plan with exercises or None
    """
    plan = await get_latest_plan(student_id)
    if not plan:
        return None
    
    exercises = await get_plan_exercises(plan["id"])
    plan["exercises"] = exercises
    
    return plan


async def record_workout_feedback(
    student_id: int,
    plan_id: int,
    rating: int,
    feedback_text: str = "",
    difficulty: Optional[str] = None
) -> Dict[str, Any]:
    """
    Record user feedback for a completed workout.
    
    Args:
        student_id: The student's ID
        plan_id: The workout plan ID
        rating: User rating (1-5)
        feedback_text: Optional text feedback
        difficulty: Perceived difficulty (easy, moderate, hard)
        
    Returns:
        Created feedback record
    """
    # Estimate duration based on rating and difficulty
    duration_map = {"easy": 45, "moderate": 60, "hard": 75}
    duration = duration_map.get(difficulty, 60)
    
    # Log the completion
    completion = await log_workout_completion(
        student_id=student_id,
        plan_id=plan_id,
        duration_minutes=duration,
        rating=rating,
        notes=feedback_text
    )
    
    return {
        "completion": completion,
        "feedback_recorded": True,
        "message": "Feedback recorded successfully!"
    }
