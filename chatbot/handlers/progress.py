"""
Handler for progress_check intent.
Shows user progress statistics and improvements with LLM analysis.
"""

from typing import Dict, Any
from ..repository.student_repo import get_student_stats, get_interaction_history
from ..services.fatigue_service import get_recovery_timeline
from ..llm.responder import generate_llm_with_fallback
from ..llm.prompts import get_system_prompt


async def handle_progress_check(
    student_id: int,
    user_message: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Handle progress_check intent.
    
    Args:
        student_id: The student's ID
        user_message: Original user message
        use_llm: Whether to use LLM for response generation
        
    Returns:
        Response dictionary with action, message, and data
    """
    # Get student statistics
    stats = await get_student_stats(student_id)
    
    # Get interaction history
    history = await get_interaction_history(student_id, limit=10)
    
    # Get recovery timeline
    timeline_data = await get_recovery_timeline(student_id, days=14)
    
    # Build context for LLM
    context_data = {
        "stats": stats,
        "history_summary": f"{len(history)} workouts logged",
        "trend": timeline_data.get("trend", "stable"),
        "current_fatigue": timeline_data.get("current_fatigue", 50)
    }
    
    # Fallback template response
    fallback_message = _build_fallback_response(stats, timeline_data, history)
    
    # Generate LLM response or use fallback
    if use_llm:
        system_prompt = get_system_prompt("progress_check")
        message, llm_used = generate_llm_with_fallback(
            intent="progress_check",
            user_message=user_message,
            fallback_response=fallback_message,
            context_data=context_data,
            custom_system_prompt=system_prompt
        )
    else:
        message = fallback_message
        llm_used = False
    
    return {
        "action": "show_progress",
        "message": message,
        "data": {
            "stats": stats,
            "timeline": timeline_data.get("timeline", []),
            "trend": timeline_data.get("trend", "stable"),
            "recent_workouts": history[:5]
        },
        "llm_used": llm_used
    }


def _build_fallback_response(
    stats: Dict[str, Any],
    timeline_data: Dict[str, Any],
    history: list
) -> str:
    """Build formatted fallback response."""
    total_workouts = stats.get("total_workouts", 0)
    completion_rate = stats.get("completion_rate", 0) * 100
    weeks_active = stats.get("weeks_active", 0)
    avg_per_week = stats.get("average_workouts_per_week", 0)
    trend = timeline_data.get("trend", "stable")
    
    # Trend emoji
    trend_emoji = {
        "improving": "📈",
        "declining": "📉",
        "stable": "➡️"
    }.get(trend, "➡️")
    
    # Achievement badges
    badges = []
    if total_workouts >= 50:
        badges.append("🏆 50+ Workouts")
    if completion_rate >= 90:
        badges.append("💯 90%+ Completion")
    if weeks_active >= 8:
        badges.append("🔥 8+ Weeks Active")
    if avg_per_week >= 4:
        badges.append("⚡ 4+ Workouts/Week")
    
    badges_str = " ".join(badges) if badges else "Keep building your streak!"
    
    message = (
        f"## Your Progress Report {trend_emoji}\n\n"
        f"{badges_str}\n\n"
        f"### Key Statistics:\n"
        f"- **Total Workouts**: {total_workouts}\n"
        f"- **Completion Rate**: {completion_rate:.0f}%\n"
        f"- **Weeks Active**: {weeks_active}\n"
        f"- **Average Workouts/Week**: {avg_per_week:.1f}\n\n"
        f"### Recovery Trend: {trend.title()}\n"
        f"Your recent fatigue levels are {trend}. "
        f"{'Great consistency!' if trend == 'improving' else 'Keep showing up!'}\n\n"
        f"### Recent Activity:\n"
        f"You've completed {len(history)} workout sessions. "
        f"Every session brings you closer to your goals! 💪\n\n"
        f"{'🎉 Amazing progress!' if total_workouts > 30 else '🌟 Great start - keep it going!'}"
    )
    
    return message
