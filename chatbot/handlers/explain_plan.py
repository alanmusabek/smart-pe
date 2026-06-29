"""
Handler for explain_plan intent.
Explains workout plan rationale with LLM-enhanced responses.
"""

from typing import Dict, Any
from ..services.workout_service import get_current_plan_with_exercises
from ..repository.student_repo import get_student_profile
from ..llm.responder import generate_llm_with_fallback
from ..llm.prompts import get_system_prompt


async def handle_explain_plan(
    student_id: int,
    user_message: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Handle explain_plan intent.
    
    Args:
        student_id: The student's ID
        user_message: Original user message
        use_llm: Whether to use LLM for response generation
        
    Returns:
        Response dictionary with action, message, and data
    """
    # Get current plan with exercises
    plan_data = await get_current_plan_with_exercises(student_id)
    
    if not plan_data:
        return {
            "action": "explain_plan",
            "message": "I couldn't find an active workout plan for you. Would you like me to generate a new one?",
            "data": {"plan": None},
            "llm_used": False
        }
    
    # Get student profile for context
    profile = await get_student_profile(student_id)
    
    # Build context for LLM
    context_data = {
        "current_plan": plan_data,
        "exercises": plan_data.get("exercises", []),
        "user_question": user_message,
        "profile": profile
    }
    
    # Fallback template response
    fallback_message = _build_fallback_response(plan_data, profile)
    
    # Generate LLM response or use fallback
    if use_llm:
        system_prompt = get_system_prompt("explain_plan")
        message, llm_used = generate_llm_with_fallback(
            intent="explain_plan",
            user_message=user_message,
            fallback_response=fallback_message,
            context_data=context_data,
            custom_system_prompt=system_prompt
        )
    else:
        message = fallback_message
        llm_used = False
    
    return {
        "action": "explain_plan",
        "message": message,
        "data": {
            "plan": plan_data,
            "profile": profile
        },
        "llm_used": llm_used
    }


def _build_fallback_response(
    plan_data: Dict[str, Any],
    profile: Dict[str, Any]
) -> str:
    """
    Build a formatted fallback response without LLM.
    
    Args:
        plan_data: Current plan data with exercises
        profile: Student profile
        
    Returns:
        Formatted response string
    """
    plan_name = plan_data.get("name", "Your Workout Plan")
    plan_description = plan_data.get("description", "")
    exercises = plan_data.get("exercises", [])
    fitness_level = profile.get("fitness_level", "intermediate")
    goals = profile.get("goals", [])
    
    # Build exercise explanations
    exercise_explanations = []
    exercise_rationales = {
        "Squat": "Compound movement for overall leg strength and power development",
        "Deadlift": "Posterior chain developer targeting hamstrings, glutes, and back",
        "Bench Press": "Primary horizontal pushing movement for chest, shoulders, and triceps",
        "Row": "Horizontal pulling for back thickness and posture improvement",
        "Overhead Press": "Vertical pushing for shoulder strength and stability",
        "Pull-up": "Vertical pulling for lat width and upper back strength",
        "Plank": "Isometric core stabilization for anti-extension strength",
        "Romanian Deadlift": "Hip hinge pattern focusing on hamstring lengthening and glute activation",
        "Lunge": "Unilateral leg work for balance, stability, and addressing imbalances",
    }
    
    for ex in exercises[:5]:  # Explain first 5 exercises
        exercise_name = ex.get("exercise_name", "")
        sets_reps = f"{ex.get('sets', 3)} sets × {ex.get('reps', '10')}"
        
        # Find matching rationale
        rationale = "Targets multiple muscle groups for efficient training"
        for key, value in exercise_rationales.items():
            if key.lower() in exercise_name.lower():
                rationale = value
                break
        
        exercise_explanations.append(
            f"**{exercise_name}** ({sets_reps}): {rationale}"
        )
    
    message = (
        f"## Why This Plan Was Chosen For You\n\n"
        f"**Plan**: {plan_name}\n"
        f"**Description**: {plan_description}\n\n"
        f"Based on your fitness level (**{fitness_level}**) and goals (**{', '.join(goals)}**), "
        f"this plan is designed to:\n\n"
        f"### Exercise Selection Rationale:\n"
        + "\n".join(f"- {ex}" for ex in exercise_explanations)
        + "\n\nEach exercise was selected to maximize your progress while considering "
        f"your available equipment and preferred training style. The volume and intensity "
        f"are periodized to promote continuous adaptation while minimizing injury risk."
    )
    
    return message
