"""
LLM client module.
Handles communication with LLM providers (Ollama, OpenAI, etc.).
Supports streaming for faster perceived response time.
"""

import os
import logging
import time
from typing import Optional, Tuple, Dict, Any, Generator
from openai import OpenAI
from ..models import LLMConfig

# Configure detailed console logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ChatbotLLM")


class LLMClient:
    """
    Client for communicating with LLM providers.
    Supports Ollama (local) and OpenAI-compatible APIs.
    Includes streaming support for faster responses.
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
                logger.info("-" * 60)
                logger.info("🤖 Initializing LLM Client...")
                logger.info(f"   - Model: {self.config.model}")
                logger.info(f"   - Base URL: {self.config.base_url}")
                logger.info(f"   - Timeout: {self.config.timeout}s (10 min)")
                logger.info(f"   - Max Tokens: {self.config.max_tokens}")
                logger.info(f"   - Temperature: {self.config.temperature}")
                logger.info("-" * 60)
                
                self.client = OpenAI(
                    base_url=self.config.base_url,
                    api_key=self.config.api_key,
                    timeout=self.config.timeout
                )
                self.available = True
                logger.info("✅ LLM Client initialized successfully!")
            except Exception as e:
                logger.error(f"❌ Failed to initialize LLM Client: {e}", exc_info=True)
                self.available = False
        else:
            logger.warning("⚠️  LLM is disabled via environment variables.")
    
    def _load_config_from_env(self) -> LLMConfig:
        """Load LLM configuration from environment variables."""
        return LLMConfig(
            enabled=os.getenv("LLM_ENABLED", "true").lower() == "true",
            base_url=os.getenv("LLM_BASE_URL", "http://localhost:11434/v1"),
            api_key=os.getenv("LLM_API_KEY", "ollama"),
            model=os.getenv("LLM_MODEL", "qwen2.5:3b"),  # Changed to qwen2.5:3b
            timeout=int(os.getenv("LLM_TIMEOUT", "600")),  # 10 minutes
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "150")),  # Reduced to 150
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7"))
        )
    
    def generate_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """
        Stream a response from the LLM token by token.
        
        Args:
            system_prompt: System instruction prompt
            user_prompt: User message prompt
            context: Optional context data to include
            
        Yields:
            Chunks of text as they are generated
        """
        if not self.available or not self.client:
            logger.warning("⚠️  LLM Client not available. Yielding empty stream.")
            yield ""
            return
        
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
        
        logger.info("-" * 60)
        logger.info("📡 Sending request to LLM...")
        logger.info(f"   Model: {self.config.model}")
        logger.info(f"   System Prompt (first 100 chars): {system_prompt[:100]}...")
        logger.info(f"   User Prompt (first 100 chars): {user_prompt[:100]}...")
        if context:
            logger.info(f"   Context keys: {list(context.keys())}")
        logger.info("-" * 60)
        
        start_time = time.time()
        
        try:
            # Enable streaming for faster initial response
            stream = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=True,  # Enable streaming
                timeout=self.config.timeout
            )
            
            logger.info("⏳ Receiving stream...")
            chunk_count = 0
            total_chars = 0
            
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        content = delta.content
                        total_chars += len(content)
                        chunk_count += 1
                        
                        # Log periodically to avoid spam
                        if chunk_count <= 3 or chunk_count % 5 == 1:
                            logger.debug(f"   Chunk #{chunk_count}: '{content.strip()}'")
                        
                        yield content
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info("-" * 60)
            logger.info("✅ LLM Response Complete!")
            logger.info(f"   Duration: {duration:.2f}s")
            logger.info(f"   Total Chunks: {chunk_count}")
            logger.info(f"   Total Characters: {total_chars}")
            logger.info("-" * 60)
            
        except Exception as e:
            logger.error(f"❌ LLM Stream Error: {e}", exc_info=True)
            yield f"[Error generating response: {str(e)}]"
    
    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[str], bool]:
        """
        Generate a response using the LLM (collects full stream).
        
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
        
        full_response = ""
        for chunk in self.generate_stream(system_prompt, user_prompt, context):
            full_response += chunk
        
        # Check if response was an error
        if full_response.startswith("[Error generating response:"):
            return None, False
        
        return full_response.strip() if full_response else None, True
    
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


def generate_llm_response_stream(
    system_prompt: str,
    user_prompt: str,
    context: Optional[Dict[str, Any]] = None
) -> Generator[str, None, None]:
    """Convenience function to stream LLM response using singleton."""
    return get_llm_client().generate_stream(system_prompt, user_prompt, context)
