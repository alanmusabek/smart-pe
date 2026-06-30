"""
Fatigue service for business logic.
Orchestrates fatigue analysis, recovery scoring, and recommendations.
"""

from typing import Dict, Any, List, Optional
from ..repository import (
    get_muscle_fatigue,
    get_fatigue_history,
    calculate_recovery_score,
    get_rest_recommendations,
)


async def get_fatigue_analysis(student_id: int) -> Dict[str, Any]:
    """
    Get comprehensive fatigue analysis for a student.
    
    Args:
        student_id: The student's ID
        
    Returns:
        Complete fatigue analysis with scores and recommendations
    """
    # Get current fatigue data
    fatigue_data = await get_muscle_fatigue(student_id)
    
    # Calculate recovery score
    recovery_info = await calculate_recovery_score(student_id)
    
    # Get rest recommendations
    rest_recs = await get_rest_recommendations(student_id)
    
    return {
        "fatigue_data": fatigue_data,
        "recovery_score": recovery_info["recovery_score"],
        "readiness_level": recovery_info["readiness_level"],
        "recommendation": recovery_info["recommendation"],
        "most_fatigued": recovery_info["most_fatigued"],
        "most_recovered": recovery_info["most_recovered"],
        "needs_rest": rest_recs["needs_rest"],
        "ready_to_train": rest_recs["ready_to_train"],
        "suggested_focus": rest_recs["suggested_focus"]
    }


async def get_recovery_timeline(student_id: int, days: int = 7) -> Dict[str, Any]:
    """
    Get recovery timeline and trends.
    
    Args:
        student_id: The student's ID
        days: Number of days to analyze
        
    Returns:
        Timeline data with trends
    """
    history = await get_fatigue_history(student_id, days)
    
    if not history:
        return {"timeline": [], "trend": "stable"}
    
    # Calculate trend (improving, declining, stable)
    recent_avg = sum(h["overall_fatigue"] for h in history[:3]) / min(3, len(history))
    older_avg = sum(h["overall_fatigue"] for h in history[-3:]) / min(3, len(history))
    
    if recent_avg < older_avg - 5:
        trend = "improving"
    elif recent_avg > older_avg + 5:
        trend = "declining"
    else:
        trend = "stable"
    
    return {
        "timeline": history,
        "trend": trend,
        "current_fatigue": history[0]["overall_fatigue"] if history else 0,
        "average_fatigue": sum(h["overall_fatigue"] for h in history) / len(history)
    }


async def get_training_readiness(student_id: int) -> Dict[str, Any]:
    """
    Determine if student is ready to train and what type of training.
    
    Args:
        student_id: The student's ID
        
    Returns:
        Readiness assessment with recommendations
    """
    analysis = await get_fatigue_analysis(student_id)
    
    readiness_level = analysis["readiness_level"]
    
    if readiness_level == "excellent":
        return {
            "ready": True,
            "intensity": "high",
            "recommendation": "Perfect day for an intense workout! Focus on heavy compounds or PR attempts.",
            "suggested_workout_type": "strength_power",
            "avoid": []
        }
    elif readiness_level == "good":
        return {
            "ready": True,
            "intensity": "moderate",
            "recommendation": "Good to train! Focus on moderate intensity with good volume.",
            "suggested_workout_type": "hypertrophy",
            "avoid": analysis["needs_rest"]
        }
    elif readiness_level == "fair":
        return {
            "ready": True,
            "intensity": "light",
            "recommendation": "You can train but keep it light. Focus on technique and mobility.",
            "suggested_workout_type": "active_recovery",
            "avoid": analysis["needs_rest"]
        }
    else:  # poor
        return {
            "ready": False,
            "intensity": "rest",
            "recommendation": "Rest day recommended. Focus on sleep, nutrition, and light movement.",
            "suggested_workout_type": "rest",
            "avoid": ["all_intense_training"]
        }


async def get_muscle_group_status(student_id: int, muscle_group: str) -> Dict[str, Any]:
    """
    Get detailed status for a specific muscle group.
    
    Args:
        student_id: The student's ID
        muscle_group: Name of the muscle group
        
    Returns:
        Status information for the muscle group
    """
    fatigue_data = await get_muscle_fatigue(student_id)
    
    fatigue_level = fatigue_data.get(muscle_group, 50)
    
    if fatigue_level < 30:
        status = "fully_recovered"
        description = "This muscle group is fully recovered and ready for intense work."
    elif fatigue_level < 50:
        status = "mostly_recovered"
        description = "This muscle group is mostly recovered. Moderate training is appropriate."
    elif fatigue_level < 70:
        status = "partially_fatigued"
        description = "This muscle group still has some fatigue. Light training or rest recommended."
    else:
        status = "fatigued"
        description = "This muscle group is significantly fatigued. Rest is strongly recommended."
    
    return {
        "muscle_group": muscle_group,
        "fatigue_level": fatigue_level,
        "status": status,
        "description": description,
        "ready_to_train": fatigue_level < 50,
        "recommended_rest_days": max(0, (fatigue_level - 30) // 20)
    }
