"""
Pydantic models for the chatbot module.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class ChatMessage(BaseModel):
    """Request model for chat messages."""
    text: str = Field(..., min_length=1, max_length=2000, description="The user's message text")


class IntentResult(BaseModel):
    """Result of intent classification."""
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)
    matched_patterns: List[str] = []


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    intent: str
    confidence: float
    message: str
    action: str
    data: Optional[Dict[str, Any]] = None
    llm_used: bool = False
    metadata: Optional[Dict[str, Any]] = None


class LLMConfig(BaseModel):
    """Configuration for LLM client."""
    enabled: bool = True
    base_url: str = "http://localhost:11434/v1"
    api_key: str = "ollama"
    model: str = "llama3.1:8b"
    timeout: int = 15
    max_tokens: int = 500
    temperature: float = 0.7
