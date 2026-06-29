"""
Handler for check_fatigue intent.
Analyzes muscle fatigue and provides recovery recommendations with LLM.
"""

from typing import Dict, Any
from ..services.fatigue_service import (
    get_fatigue_analysis,
    get_training_readiness,
)
from ..llm.responder import generate_llm_with_fallback
from ..llm.prompts import get_system_prompt


async def handle_check_fatigue(
    student_id: int,
    user_message: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Handle check_fatigue intent.
    
    Args:
        student_id: The student's ID
        user_message: Original user message
        use_llm: Whether to use LLM for response generation
        
    Returns:
        Response dictionary with action, message, and data
    """
    # Get comprehensive fatigue analysis
    analysis = await get_fatigue_analysis(student_id)
    readiness = await get_training_readiness(student_id)
    
    # Build context for LLM
    context_data = {
        "fatigue_data": analysis["fatigue_data"],
        "recovery_score": analysis["recovery_score"],
        "readiness_level": analysis["readiness_level"],
        "most_fatigued": analysis["most_fatigued"],
        "most_recovered": analysis["most_recovered"],
        "needs_rest": analysis["needs_rest"],
        "ready_to_train": analysis["ready_to_train"]
    }
    
    # Fallback template response
    fallback_message = _build_fallback_response(analysis, readiness)
    
    # Generate LLM response or use fallback
    if use_llm:
        system_prompt = get_system_prompt("check_fatigue")
        message, llm_used = generate_llm_with_fallback(
            intent="check_fatigue",
            user_message=user_message,
            fallback_response=fallback_message,
            context_data=context_data,
            custom_system_prompt=system_prompt
        )
    else:
        message = fallback_message
        llm_used = False
    
    return {
        "action": "show_fatigue",
        "message": message,
        "data": {
            "fatigue_data": analysis["fatigue_data"],
            "recovery_score": analysis["recovery_score"],
            "readiness_level": analysis["readiness_level"],
            "recommendation": analysis["recommendation"],
            "training_readiness": readiness
        },
        "llm_used": llm_used
    }


def _build_fallback_response(
    analysis: Dict[str, Any],
    readiness: Dict[str, Any]
) -> str:
    """
    Build a formatted fallback response without LLM.
    
    Args:
        analysis: Fatigue analysis data
        readiness: Training readiness data
        
    Returns:
        Formatted response string
    """
    recovery_score = analysis["recovery_score"]
    readiness_level = analysis["readiness_level"]
    
    # Build muscle status summary
    fatigue_data = analysis["fatigue_data"]
    muscle_status = []
    
    # Sort by fatigue level (highest first)
    sorted_muscles = sorted(fatigue_data.items(), key=lambda x: x[1], reverse=True)
    
    for muscle, fatigue in sorted_muscles[:5]:  # Top 5 most fatigued
        if fatigue > 70:
            status = "🔴 High fatigue"
        elif fatigue > 50:
            status = "🟡 Moderate fatigue"
        elif fatigue > 30:
            status = "🟢 Mostly recovered"
        else:
            status = "✅ Fully recovered"
        
        muscle_status.append(f"- **{muscle.capitalize()}**: {fatigue}% - {status}")
    
    message = (
        f"## Recovery Status Report\n\n"
        f"**Overall Recovery Score**: {recovery_score}/100\n"
        f"**Readiness Level**: {readiness_level.upper()}\n\n"
        f"### Muscle Group Status (Most Fatigued First):\n"
        + "\n".join(muscle_status)
        + f"\n\n### Recommendation:\n{analysis['recommendation']}\n\n"
        f"**Training Advice**: {readiness['recommendation']}"
    )
    
    return message
