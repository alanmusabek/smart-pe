"""
Intent definitions for the chatbot.
Each intent has a name, description, and associated action.
"""

from typing import List, Dict


class IntentDefinition:
    """Represents a chatbot intent."""
    
    def __init__(self, name: str, description: str, action: str, keywords: List[str] = None):
        self.name = name
        self.description = description
        self.action = action
        self.keywords = keywords or []


# All supported intents
INTENTS = {
    "generate_workout": IntentDefinition(
        name="generate_workout",
        description="The user wants to create, generate, or get a new workout plan.",
        action="plan_generated",
        keywords=[
            "generate", "create", "new plan", "workout", "exercise plan",
            "training plan", "routine", "session", "today's workout"
        ]
    ),
    "check_fatigue": IntentDefinition(
        name="check_fatigue",
        description="The user wants to check their muscle fatigue, recovery status, or soreness.",
        action="show_fatigue",
        keywords=[
            "fatigue", "recovery", "sore", "tired", "muscle", "recover",
            "status", "ready", "rest", "ache", "pain"
        ]
    ),
    "explain_plan": IntentDefinition(
        name="explain_plan",
        description="The user wants to understand why the AI chose specific exercises or plan structure.",
        action="explain_plan",
        keywords=[
            "why", "explain", "reason", "choose", "selected", "purpose",
            "benefit", "target", "focus", "goal"
        ]
    ),
    "record_feedback": IntentDefinition(
        name="record_feedback",
        description="The user wants to submit feedback, rate a workout, or log an exercise completion.",
        action="feedback_recorded",
        keywords=[
            "feedback", "rate", "rating", "log", "completed", "finished",
            "difficult", "easy", "hard", "score", "review"
        ]
    ),
    "exercise_recommendation": IntentDefinition(
        name="exercise_recommendation",
        description="The user wants exercise suggestions for specific muscle groups or goals.",
        action="show_recommendations",
        keywords=[
            "recommend", "suggest", "exercise for", "best exercise",
            "what exercise", "should i do", "target", "specific"
        ]
    ),
    "progress_check": IntentDefinition(
        name="progress_check",
        description="The user wants to view their progress statistics and improvements over time.",
        action="show_progress",
        keywords=[
            "progress", "improvement", "stats", "statistics", "history",
            "track", "improved", "better", "personal record", "pr"
        ]
    ),
    "general_chat": IntentDefinition(
        name="general_chat",
        description="The user is greeting, asking for help, or having general conversation.",
        action="chat",
        keywords=[
            "hello", "hi", "hey", "help", "what can you", "how to",
            "thanks", "thank you", "goodbye", "bye", "who are you"
        ]
    )
}

# Ordered list of intent names for classification priority
INTENT_ORDER = [
    "generate_workout",
    "check_fatigue", 
    "explain_plan",
    "record_feedback",
    "exercise_recommendation",
    "progress_check",
    "general_chat"
]


def get_intent_names() -> List[str]:
    """Get list of all intent names."""
    return list(INTENTS.keys())


def get_intent_description(intent_name: str) -> str:
    """Get description for a specific intent."""
    intent = INTENTS.get(intent_name)
    return intent.description if intent else "Unknown intent"


def get_intent_action(intent_name: str) -> str:
    """Get action for a specific intent."""
    intent = INTENTS.get(intent_name)
    return intent.action if intent else "chat"


def get_intent_keywords(intent_name: str) -> List[str]:
    """Get keywords for a specific intent."""
    intent = INTENTS.get(intent_name)
    return intent.keywords if intent else []
