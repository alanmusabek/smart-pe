"""
Context builder module.
Builds and manages conversation context for LLM interactions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class ConversationContext:
    """Manages conversation context for a user session."""
    
    def __init__(self, student_id: int):
        self.student_id = student_id
        self.message_history: List[Dict[str, Any]] = []
        self.current_intent: Optional[str] = None
        self.last_intent: Optional[str] = None
        self.session_data: Dict[str, Any] = {}
        self.created_at = datetime.now()
    
    def add_message(self, role: str, content: str, intent: Optional[str] = None):
        """Add a message to the conversation history."""
        self.message_history.append({
            "role": role,
            "content": content,
            "intent": intent,
            "timestamp": datetime.now().isoformat()
        })
        
        if intent:
            self.last_intent = self.current_intent
            self.current_intent = intent
    
    def get_recent_messages(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent messages from history."""
        return self.message_history[-limit:]
    
    def get_context_summary(self) -> str:
        """Build a summary of the conversation context."""
        if not self.message_history:
            return "New conversation."
        
        intents_mentioned = set()
        for msg in self.message_history:
            if msg.get("intent"):
                intents_mentioned.add(msg["intent"])
        
        return f"Conversation with {len(self.message_history)} messages. Intents discussed: {', '.join(intents_mentioned)}"
    
    def clear_history(self, keep_last: int = 0):
        """Clear message history, optionally keeping last N messages."""
        if keep_last > 0:
            self.message_history = self.message_history[-keep_last:]
        else:
            self.message_history = []


# Context storage (in production, use Redis or database)
_context_store: Dict[int, ConversationContext] = {}


def get_or_create_context(student_id: int) -> ConversationContext:
    """Get existing context or create new one for student."""
    if student_id not in _context_store:
        _context_store[student_id] = ConversationContext(student_id)
    return _context_store[student_id]


def update_context(
    student_id: int,
    user_message: str,
    assistant_response: str,
    intent: str
) -> ConversationContext:
    """Update context with new message pair."""
    context = get_or_create_context(student_id)
    context.add_message("user", user_message, intent)
    context.add_message("assistant", assistant_response, intent)
    return context


def get_context_for_llm(student_id: int, include_history: bool = True) -> Dict[str, Any]:
    """
    Build context dictionary for LLM consumption.
    
    Args:
        student_id: The student's ID
        include_history: Whether to include message history
        
    Returns:
        Context dictionary ready for LLM
    """
    context = get_or_create_context(student_id)
    
    llm_context = {
        "student_id": student_id,
        "current_intent": context.current_intent,
        "last_intent": context.last_intent,
        "message_count": len(context.message_history),
        "session_duration_minutes": (datetime.now() - context.created_at).total_seconds() / 60
    }
    
    if include_history:
        llm_context["recent_messages"] = context.get_recent_messages(limit=3)
    
    # Add any session-specific data
    llm_context.update(context.session_data)
    
    return llm_context


def clear_student_context(student_id: int):
    """Clear all context for a student."""
    if student_id in _context_store:
        del _context_store[student_id]
