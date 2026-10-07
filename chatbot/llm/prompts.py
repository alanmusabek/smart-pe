"""
LLM prompts module.
Contains all prompt templates for different chatbot intents.
"""

from typing import Dict, Any, Optional


# System prompts for different intents
SYSTEM_PROMPTS = {
    "generate_workout": (
        "You are an expert, encouraging personal trainer. Your role is to create motivating, "
        "personalized workout plans that are safe and effective. Always explain the purpose of "
        "each exercise and provide form cues. Keep responses friendly, supportive, and actionable."
    ),
    "check_fatigue": (
        "You are an analytical sports scientist specializing in recovery and fatigue management. "
        "Your role is to interpret muscle fatigue data and provide clear, actionable recommendations. "
        "Be encouraging but honest about recovery status. Help users understand when to push and when to rest."
    ),
    "explain_plan": (
        "You are an insightful AI coach who excels at explaining training methodology. "
        "Your role is to help users understand the 'why' behind their workout plans. "
        "Use clear, educational language and connect exercise choices to specific goals and adaptations."
    ),
    "record_feedback": (
        "You are a supportive fitness coach who values user feedback. "
        "Your role is to acknowledge feedback positively and use it to improve future recommendations. "
        "Celebrate completions and address concerns constructively."
    ),
    "exercise_recommendation": (
        "You are a knowledgeable exercise specialist. Your role is to recommend appropriate exercises "
        "based on user goals, available equipment, and current fitness level. "
        "Always include form tips and progression options."
    ),
    "progress_check": (
        "You are a motivational data analyst who helps users see their fitness journey clearly. "
        "Your role is to present progress data in an encouraging way, highlighting improvements "
        "and identifying areas for continued growth. Celebrate wins and set positive future directions."
    ),
    "general_chat": (
        "You are a helpful, friendly Smart PE AI assistant. "
        "Your role is to assist users with questions, provide encouragement, and guide them "
        "to relevant features like workout generation, fatigue checking, or progress tracking. "
        "Be conversational, warm, and helpful."
    )
}


def get_system_prompt(intent: str, custom_additions: Optional[str] = None) -> str:
    """
    Get system prompt for a specific intent.
    
    Args:
        intent: The intent name
        custom_additions: Optional additional instructions to append
        
    Returns:
        Complete system prompt string
    """
    base_prompt = SYSTEM_PROMPTS.get(intent, SYSTEM_PROMPTS["general_chat"])
    
    if custom_additions:
        return f"{base_prompt}\n\n{custom_additions}"
    
    return base_prompt


def build_user_prompt(
    intent: str,
    user_message: str,
    context_data: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build user prompt with context for a specific intent.
    
    Args:
        intent: The intent name
        user_message: Original user message
        context_data: Optional context data to include
        
    Returns:
        Formatted user prompt string
    """
    prompt_parts = [f"The user said: '{user_message}'"]
    
    # Add context-specific information based on intent
    if intent == "generate_workout" and context_data:
        if "profile" in context_data:
            profile = context_data["profile"]
            prompt_parts.append(
                f"\nUser Profile:\n"
                f"- Fitness Level: {profile.get('fitness_level', 'not specified')}\n"
                f"- Goals: {', '.join(profile.get('goals', []))}\n"
                f"- Preferred Days: {', '.join(profile.get('preferred_workout_days', []))}"
            )
        if "preferences" in context_data:
            prefs = context_data["preferences"]
            prompt_parts.append(
                f"\nPreferences:\n"
                f"- Duration: {prefs.get('workout_duration', 60)} minutes\n"
                f"- Equipment: {', '.join(prefs.get('equipment_available', []))}\n"
                f"- Focus Areas: {', '.join(prefs.get('focus_areas', []))}"
            )
    
    elif intent == "check_fatigue" and context_data:
        if "fatigue_data" in context_data:
            fatigue = context_data["fatigue_data"]
            fatigue_str = ", ".join(f"{k}: {v}%" for k, v in fatigue.items())
            prompt_parts.append(
                f"\nCurrent Muscle Fatigue Levels (0-100%, lower = more recovered):\n{fatigue_str}"
            )
        if "recovery_score" in context_data:
            prompt_parts.append(
                f"\nOverall Recovery Score: {context_data['recovery_score']}/100"
            )
    
    elif intent == "explain_plan" and context_data:
        if "current_plan" in context_data:
            plan = context_data["current_plan"]
            prompt_parts.append(
                f"\nCurrent Plan: {plan.get('name', 'Unknown')}\n"
                f"Description: {plan.get('description', 'No description')}"
            )
        if "exercises" in context_data:
            exercises = context_data["exercises"]
            exercise_list = "\n".join(
                f"- {ex['exercise_name']}: {ex['sets']} sets x {ex['reps']}"
                for ex in exercises[:5]  # Limit to first 5
            )
            prompt_parts.append(f"\nExercises:\n{exercise_list}")
    
    elif intent == "progress_check" and context_data:
        if "stats" in context_data:
            stats = context_data["stats"]
            prompt_parts.append(
                f"\nProgress Statistics:\n"
                f"- Total Workouts: {stats.get('total_workouts', 0)}\n"
                f"- Completion Rate: {stats.get('completion_rate', 0) * 100:.0f}%\n"
                f"- Weeks Active: {stats.get('weeks_active', 0)}\n"
                f"- Avg Workouts/Week: {stats.get('average_workouts_per_week', 0)}"
            )
    
    elif intent == "exercise_recommendation" and context_data:
        if "target_muscle" in context_data:
            prompt_parts.append(f"\nTarget Muscle Group: {context_data['target_muscle']}")
        if "equipment" in context_data:
            prompt_parts.append(f"\nAvailable Equipment: {', '.join(context_data['equipment'])}")
        if "goal" in context_data:
            prompt_parts.append(f"\nPrimary Goal: {context_data['goal']}")
    
    return "\n".join(prompt_parts)


def build_context_for_llm(
    intent: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Build context dictionary for LLM generation.
    
    Args:
        intent: The intent name
        **kwargs: Various context data
        
    Returns:
        Context dictionary ready for LLM
    """
    context = {}
    
    if intent == "generate_workout":
        context.update({
            "profile": kwargs.get("profile"),
            "preferences": kwargs.get("preferences"),
            "message": kwargs.get("message")
        })
    elif intent == "check_fatigue":
        context.update({
            "fatigue_data": kwargs.get("fatigue_data"),
            "recovery_score": kwargs.get("recovery_score")
        })
    elif intent == "explain_plan":
        context.update({
            "current_plan": kwargs.get("current_plan"),
            "exercises": kwargs.get("exercises"),
            "user_question": kwargs.get("user_question")
        })
    elif intent == "progress_check":
        context.update({
            "stats": kwargs.get("stats"),
            "history": kwargs.get("history")
        })
    elif intent == "exercise_recommendation":
        context.update({
            "target_muscle": kwargs.get("target_muscle"),
            "equipment": kwargs.get("equipment"),
            "goal": kwargs.get("goal")
        })
    
    # Remove None values
    return {k: v for k, v in context.items() if v is not None}
