"""
Handler for generate_workout intent.
Creates personalized workout plans with LLM-enhanced responses.
"""

from typing import Dict, Any, Optional
from ..services.workout_service import generate_personalized_workout
from ..repository.student_repo import get_student_profile, get_student_preferences
from ..llm.responder import generate_llm_with_fallback
from ..llm.prompts import get_system_prompt


async def handle_generate_workout(
    student_id: int,
    user_message: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Handle generate_workout intent.
    
    Args:
        student_id: The student's ID
        user_message: Original user message
        use_llm: Whether to use LLM for response generation
        
    Returns:
        Response dictionary with action, message, and data
    """
    # Extract custom focus if mentioned
    custom_focus = _extract_focus_from_message(user_message)
    
    # Generate the workout
    workout_data = await generate_personalized_workout(
        student_id=student_id,
        user_message=user_message,
        custom_focus=custom_focus
    )
    
    plan = workout_data["plan"]
    
    # Build context for LLM
    profile = await get_student_profile(student_id)
    preferences = await get_student_preferences(student_id)
    
    context_data = {
        "profile": profile,
        "preferences": preferences,
        "plan": plan,
        "exercises": plan.get("exercises", [])
    }
    
    # Fallback template response
    fallback_message = (
        f"Great! I've created a new workout plan for you: **{plan['name']}**\n\n"
        f"Here are your exercises:\n"
        + "\n".join(
            f"{i+1}. **{ex['exercise_name']}**: {ex['sets']} sets × {ex['reps']} "
            f"(rest: {ex.get('rest_seconds', 60)}s)"
            for i, ex in enumerate(plan.get("exercises", []))
        )
        + "\n\nLet's crush this workout! 💪"
    )
    
    # Generate LLM response or use fallback
    if use_llm:
        system_prompt = get_system_prompt("generate_workout")
        message, llm_used = generate_llm_with_fallback(
            intent="generate_workout",
            user_message=user_message,
            fallback_response=fallback_message,
            context_data=context_data,
            custom_system_prompt=system_prompt
        )
    else:
        message = fallback_message
        llm_used = False
    
    return {
        "action": "plan_generated",
        "message": message,
        "data": {
            "plan": plan,
            "focus_areas": workout_data.get("focus_areas", []),
            "preferences": workout_data.get("preferences", {})
        },
        "llm_used": llm_used
    }


def _extract_focus_from_message(message: str) -> Optional[str]:
    """
    Extract focus area from user message.
    
    Args:
        message: User message
        
    Returns:
        Focus area string or None
    """
    message_lower = message.lower()
    
    focus_keywords = {
        "legs": ["leg", "legs", "quad", "hamstring", "calf"],
        "chest": ["chest", "pec", "bench"],
        "back": ["back", "lats", "trap", "rhomboid"],
        "shoulders": ["shoulder", "delts", "upper body"],
        "arms": ["arm", "bicep", "tricep", "forearm"],
        "core": ["core", "abs", "oblique", "stomach"],
        "glutes": ["glute", "butt", "glam"],
    }
    
    for focus, keywords in focus_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            return focus
    
    return None
