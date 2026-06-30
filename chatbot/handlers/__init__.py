"""
Handlers package initialization.
"""

from .generate_workout import handle_generate_workout
from .fatigue import handle_check_fatigue
from .explain_plan import handle_explain_plan
from .feedback import handle_record_feedback
from .progress import handle_progress_check
from .general import handle_general_chat

__all__ = [
    "handle_generate_workout",
    "handle_check_fatigue",
    "handle_explain_plan",
    "handle_record_feedback",
    "handle_progress_check",
    "handle_general_chat",
]
