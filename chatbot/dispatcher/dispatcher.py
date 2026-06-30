"""
Dispatcher module.
Routes classified intents to appropriate handlers.
"""

from typing import Dict, Any, Optional
from ..handlers import (
    handle_generate_workout,
    handle_check_fatigue,
    handle_explain_plan,
    handle_record_feedback,
    handle_progress_check,
    handle_general_chat,
)


# Mapping of intent names to handler functions
INTENT_HANDLERS = {
    "generate_workout": handle_generate_workout,
    "check_fatigue": handle_check_fatigue,
    "explain_plan": handle_explain_plan,
    "record_feedback": handle_record_feedback,
    "exercise_recommendation": handle_general_chat,  # Fallback to general for now
    "progress_check": handle_progress_check,
    "general_chat": handle_general_chat,
}


async def dispatch_intent(
    intent: str,
    student_id: int,
    user_message: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Dispatch classified intent to the appropriate handler.
    
    Args:
        intent: The classified intent name
        student_id: The student's ID
        user_message: Original user message
        use_llm: Whether to use LLM for response generation
        
    Returns:
        Handler response dictionary
        
    Raises:
        ValueError: If intent is not recognized
    """
    handler = INTENT_HANDLERS.get(intent)
    
    if not handler:
        # Default to general_chat for unknown intents
        handler = handle_general_chat
        intent = "general_chat"
    
    # Call the handler
    return await handler(
        student_id=student_id,
        user_message=user_message,
        use_llm=use_llm
    )


def get_handler_for_intent(intent: str):
    """
    Get the handler function for a specific intent.
    
    Args:
        intent: The intent name
        
    Returns:
        Handler function or None if not found
    """
    return INTENT_HANDLERS.get(intent)


def get_all_supported_intents() -> list:
    """Get list of all supported intent names."""
    return list(INTENT_HANDLERS.keys())
