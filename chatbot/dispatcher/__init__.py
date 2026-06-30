"""
Dispatcher package initialization.
"""

from .dispatcher import dispatch_intent, get_handler_for_intent, get_all_supported_intents

__all__ = [
    "dispatch_intent",
    "get_handler_for_intent",
    "get_all_supported_intents",
]
