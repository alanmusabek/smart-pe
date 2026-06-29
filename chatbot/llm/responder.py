"""
LLM responder module.
Orchestrates LLM response generation with prompts and context.
"""

from typing import Tuple, Dict, Any, Optional
from .client import get_llm_client, LLMClient
from .prompts import (
    get_system_prompt,
    build_user_prompt,
    build_context_for_llm
)


class LLMResponder:
    """
    High-level interface for generating LLM responses.
    Handles prompt building, context injection, and response formatting.
    """
    
    def __init__(self, client: Optional[LLMClient] = None):
        """
        Initialize responder with optional custom client.
        
        Args:
            client: Optional custom LLM client instance
        """
        self.client = client or get_llm_client()
    
    def generate_response(
        self,
        intent: str,
        user_message: str,
        context_data: Optional[Dict[str, Any]] = None,
        custom_system_prompt: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Generate a complete LLM response for a given intent.
        
        Args:
            intent: The detected intent
            user_message: Original user message
            context_data: Context data from database/services
            custom_system_prompt: Optional override for system prompt
            
        Returns:
            Tuple of (response_text, llm_used_flag)
        """
        # Get system prompt
        system_prompt = custom_system_prompt or get_system_prompt(intent)
        
        # Build user prompt with context
        user_prompt = build_user_prompt(intent, user_message, context_data)
        
        # Build context dictionary for LLM
        llm_context = build_context_for_llm(intent, **(context_data or {}))
        
        # Generate response
        return self.client.generate(system_prompt, user_prompt, llm_context)
    
    def generate_with_fallback(
        self,
        intent: str,
        user_message: str,
        fallback_response: str,
        context_data: Optional[Dict[str, Any]] = None,
        custom_system_prompt: Optional[str] = None
    ) -> Tuple[str, bool]:
        """
        Generate response with fallback if LLM fails.
        
        Args:
            intent: The detected intent
            user_message: Original user message
            fallback_response: Response to use if LLM fails
            context_data: Context data from database/services
            custom_system_prompt: Optional override for system prompt
            
        Returns:
            Tuple of (response_text, llm_used_flag)
        """
        # Get system prompt
        system_prompt = custom_system_prompt or get_system_prompt(intent)
        
        # Build user prompt with context
        user_prompt = build_user_prompt(intent, user_message, context_data)
        
        # Build context dictionary for LLM
        llm_context = build_context_for_llm(intent, **(context_data or {}))
        
        # Generate with fallback
        return self.client.generate_with_fallback(
            system_prompt, user_prompt, fallback_response, llm_context
        )
    
    def is_available(self) -> bool:
        """Check if LLM is available."""
        return self.client.is_available()


# Singleton instance
_responder_instance: Optional[LLMResponder] = None


def get_llm_responder() -> LLMResponder:
    """Get or create the singleton LLM responder instance."""
    global _responder_instance
    if _responder_instance is None:
        _responder_instance = LLMResponder()
    return _responder_instance


def generate_llm_response(
    intent: str,
    user_message: str,
    context_data: Optional[Dict[str, Any]] = None
) -> Tuple[str, bool]:
    """
    Convenience function to generate LLM response.
    
    Args:
        intent: The detected intent
        user_message: Original user message
        context_data: Context data from database/services
        
    Returns:
        Tuple of (response_text, llm_used_flag)
    """
    return get_llm_responder().generate_response(intent, user_message, context_data)


def generate_llm_with_fallback(
    intent: str,
    user_message: str,
    fallback_response: str,
    context_data: Optional[Dict[str, Any]] = None
) -> Tuple[str, bool]:
    """
    Convenience function to generate LLM response with fallback.
    
    Args:
        intent: The detected intent
        user_message: Original user message
        fallback_response: Response to use if LLM fails
        context_data: Context data from database/services
        
    Returns:
        Tuple of (response_text, llm_used_flag)
    """
    return get_llm_responder().generate_with_fallback(
        intent, user_message, fallback_response, context_data
    )
