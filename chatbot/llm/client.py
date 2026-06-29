"""
LLM client module.
Handles communication with LLM providers (Ollama, OpenAI, etc.).
"""

import os
from typing import Optional, Tuple, Dict, Any
from openai import OpenAI
from ..models import LLMConfig


class LLMClient:
    """
    Client for communicating with LLM providers.
    Supports Ollama (local) and OpenAI-compatible APIs.
    """
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize LLM client.
        
        Args:
            config: LLM configuration. If None, loads from environment.
        """
        self.config = config or self._load_config_from_env()
        self.client: Optional[OpenAI] = None
        self.available = False
        
        if self.config.enabled:
            try:
                self.client = OpenAI(
                    base_url=self.config.base_url,
                    api_key=self.config.api_key,
                    timeout=self.config.timeout
                )
                self.available = True
                print(f"✅ LLM client initialized: {self.config.model} at {self.config.base_url}")
            except Exception as e:
                print(f"⚠️  LLM client initialization failed: {e}")
                self.available = False
    
    def _load_config_from_env(self) -> LLMConfig:
        """Load LLM configuration from environment variables."""
        return LLMConfig(
            enabled=os.getenv("LLM_ENABLED", "true").lower() == "true",
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("LLM_API_KEY", "ollama"),
            model=os.getenv("LLM_MODEL", "llama3.1:8b"),
            timeout=int(os.getenv("LLM_TIMEOUT", "15")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "500")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7"))
        )
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], bool]:
        """
        Generate a response using the LLM.
        
        Args:
            system_prompt: System instruction prompt
            user_prompt: User message prompt
            context: Optional context data to include
            
        Returns:
            Tuple of (response_text, llm_used_flag)
            If LLM is unavailable, returns (None, False)
        """
        if not self.available or not self.client:
            return None, False
        
        # Build messages
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # Add context if provided
        if context:
            context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
            messages.append({
                "role": "system",
                "content": f"Context:\n{context_str}"
            })
        
        messages.append({"role": "user", "content": user_prompt})
        
        try:
            completion = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens
            )
            
            response = completion.choices[0].message.content
            return response.strip() if response else None, True
            
        except Exception as e:
            print(f"❌ LLM generation error: {e}")
            return None, False
    
    def generate_with_fallback(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback_response: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, bool]:
        """
        Generate response with fallback if LLM fails.
        
        Args:
            system_prompt: System instruction prompt
            user_prompt: User message prompt
            fallback_response: Response to use if LLM fails
            context: Optional context data
            
        Returns:
            Tuple of (response_text, llm_used_flag)
        """
        response, used_llm = self.generate(system_prompt, user_prompt, context)
        
        if response is None:
            return fallback_response, False
        
        return response, used_llm
    
    def is_available(self) -> bool:
        """Check if LLM client is available and ready."""
        return self.available and self.client is not None


# Singleton instance
_llm_client_instance: Optional[LLMClient] = None


def get_llm_client(config: Optional[LLMConfig] = None) -> LLMClient:
    """Get or create the singleton LLM client instance."""
    global _llm_client_instance
    if _llm_client_instance is None:
        _llm_client_instance = LLMClient(config)
    return _llm_client_instance


def generate_llm_response(
    system_prompt: str,
    user_prompt: str,
    context: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[str], bool]:
    """Convenience function to generate LLM response using singleton."""
    return get_llm_client().generate(system_prompt, user_prompt, context)
