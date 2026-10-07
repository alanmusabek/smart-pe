"""
Handler for record_feedback intent.
Processes workout feedback and ratings.
"""

from typing import Dict, Any
from ..services.workout_service import record_workout_feedback
from ..services.workout_service import get_current_plan_with_exercises
from ..llm.responder import generate_llm_with_fallback
from ..llm.prompts import get_system_prompt


async def handle_record_feedback(
    student_id: int,
    user_message: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Handle record_feedback intent.
    
    Args:
        student_id: The student's ID
        user_message: Original user message
        use_llm: Whether to use LLM for response generation
        
    Returns:
        Response dictionary with action, message, and data
    """
    # Extract rating from message
    rating = _extract_rating(user_message)
    difficulty = _extract_difficulty(user_message)
    feedback_text = user_message
    
    # Get current plan to associate feedback
    plan_data = await get_current_plan_with_exercises(student_id)
    plan_id = plan_data["id"] if plan_data else 1  # Default if no plan
    
    # Record the feedback
    result = await record_workout_feedback(
        student_id=student_id,
        plan_id=plan_id,
        rating=rating or 4,  # Default rating
        feedback_text=feedback_text,
        difficulty=difficulty
    )
    
    # Build context for LLM
    context_data = {
        "rating": rating,
        "difficulty": difficulty,
        "feedback": feedback_text,
        "plan_name": plan_data.get("name", "your workout") if plan_data else "your workout"
    }
    
    # Fallback template response
    fallback_message = _build_fallback_response(rating, difficulty, plan_data)
    
    # Generate LLM response or use fallback
    if use_llm:
        system_prompt = get_system_prompt("record_feedback")
        message, llm_used = generate_llm_with_fallback(
            intent="record_feedback",
            user_message=user_message,
            fallback_response=fallback_message,
            context_data=context_data,
            custom_system_prompt=system_prompt
        )
    else:
        message = fallback_message
        llm_used = False
    
    return {
        "action": "feedback_recorded",
        "message": message,
        "data": {
            "feedback_recorded": True,
            "rating": rating,
            "difficulty": difficulty,
            "completion": result.get("completion")
        },
        "llm_used": llm_used
    }


def _extract_rating(message: str) -> int:
    """Extract numeric rating from message."""
    import re
    # Look for patterns like "4/5", "4 stars", "rating: 4", etc.
    patterns = [
        r'(\d)\s*/\s*5',
        r'(\d)\s*stars?',
        r'rating[:\s]+(\d)',
        r'rated?\s*(\d)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            rating = int(match.group(1))
            return min(5, max(1, rating))  # Clamp to 1-5
    
    return None


def _extract_difficulty(message: str) -> str:
    """Extract difficulty level from message."""
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["easy", "light", "simple"]):
        return "easy"
    elif any(word in message_lower for word in ["hard", "difficult", "challenging", "tough"]):
        return "hard"
    elif any(word in message_lower for word in ["moderate", "medium", "okay", "ok"]):
        return "moderate"
    
    return None


def _build_fallback_response(
    rating: int,
    difficulty: str,
    plan_data: Dict[str, Any]
) -> str:
    """Build formatted fallback response."""
    rating_emoji = {
        5: "🌟🌟🌟🌟🌟",
        4: "🌟🌟🌟🌟☆",
        3: "🌟🌟🌟☆☆",
        2: "🌟🌟☆☆☆",
        1: "🌟☆☆☆☆"
    }
    
    emoji = rating_emoji.get(rating, "🌟🌟🌟🌟☆") if rating else "Thank you!"
    
    plan_name = plan_data.get("name", "your workout") if plan_data else "your workout"
    
    message = (
        f"{emoji}\n\n"
        f"Thanks for your feedback on **{plan_name}**! \n\n"
        f"Your rating has been recorded. We'll use this information to "
        f"personalize your future workouts. Keep up the great work! 💪\n\n"
        f"{'Great job crushing it!' if rating and rating >= 4 else 'Keep pushing - every workout counts!'}"
    )
    
    return message
