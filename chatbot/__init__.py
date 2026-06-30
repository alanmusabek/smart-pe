"""
Smart PE Chatbot Module
A modular, high-performance chatbot with LLM integration and database connectivity.

Structure:
├── classifier/     - Intent classification (fast pattern matching)
├── dispatcher/     - Routes intents to handlers
├── handlers/       - Intent-specific response handlers
├── services/       - Business logic layer
├── context/        - Conversation context management
├── llm/            - LLM client and prompt management
├── repository/     - Database access layer
└── models.py       - Pydantic models
"""

from .models import ChatMessage, ChatResponse, IntentResult, LLMConfig
from .classifier import get_classifier, classify_intent, INTENTS
from .dispatcher import dispatch_intent
from .llm import get_llm_client, get_llm_responder
from .context import get_or_create_context, update_context

__all__ = [
    # Models
    "ChatMessage",
    "ChatResponse", 
    "IntentResult",
    "LLMConfig",
    # Classifier
    "get_classifier",
    "classify_intent",
    "INTENTS",
    # Dispatcher
    "dispatch_intent",
    # LLM
    "get_llm_client",
    "get_llm_responder",
    # Context
    "get_or_create_context",
    "update_context",
]
