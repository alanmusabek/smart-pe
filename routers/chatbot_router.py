"""
Chatbot router for FastAPI.
Main entry point for chatbot API endpoints.
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# Import from chatbot module
from ..chatbot import (
    ChatMessage,
    ChatResponse,
    classify_intent,
    dispatch_intent,
    INTENTS,
    get_or_create_context,
    update_context,
)
from ..chatbot.llm import get_llm_client

router = APIRouter(prefix="/chat", tags=["Chatbot"])


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    text: str
    use_llm: Optional[bool] = True  # Allow disabling LLM per request


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: Dict[str, Any] = Depends(lambda: {"id": 1})  # TODO: Replace with actual auth
):
    """
    Main chat endpoint.
    
    Classifies user intent, executes appropriate handler, and returns
    a personalized response with optional LLM enhancement.
    
    ## Features:
    - **Fast intent classification** (~0.5ms using pattern matching)
    - **LLM-enhanced responses** (configurable, with graceful fallback)
    - **Database integration** (student profiles, fatigue data, workout history)
    - **7 supported intents**: generate_workout, check_fatigue, explain_plan,
      record_feedback, exercise_recommendation, progress_check, general_chat
    
    ## Environment Variables:
    - `LLM_ENABLED`: Enable/disable LLM (default: true)
    - `LLM_BASE_URL`: LLM API endpoint (default: http://localhost:11434/v1)
    - `LLM_MODEL`: Model name (default: llama3.1:8b)
    - `LLM_TIMEOUT`: Request timeout in seconds (default: 15)
    - `LLM_MAX_TOKENS`: Max response tokens (default: 500)
    - `LLM_TEMPERATURE`: Response creativity (default: 0.7)
    
    ## Example:
    ```bash
    curl -X POST http://localhost:8000/chat/ \\
      -H "Content-Type: application/json" \\
      -d '{"text": "generate a workout plan"}'
    ```
    """
    # Validate input
    if not request.text or not request.text.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    
    student_id = user.get("id", 1)  # Default to 1 for testing
    user_message = request.text.strip()
    
    # 1. Classify intent (fast pattern matching, ~0.5ms)
    intent, confidence, matched_patterns = classify_intent(user_message)
    
    # 2. Get or create conversation context
    context = get_or_create_context(student_id)
    
    # 3. Dispatch to appropriate handler
    try:
        handler_response = await dispatch_intent(
            intent=intent,
            student_id=student_id,
            user_message=user_message,
            use_llm=request.use_llm
        )
    except Exception as e:
        print(f"❌ Handler error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
    
    # 4. Update conversation context
    update_context(
        student_id=student_id,
        user_message=user_message,
        assistant_response=handler_response.get("message", ""),
        intent=intent
    )
    
    # 5. Build and return response
    return ChatResponse(
        intent=intent,
        confidence=round(confidence, 3),
        message=handler_response.get("message", ""),
        action=handler_response.get("action", "chat"),
        data=handler_response.get("data"),
        llm_used=handler_response.get("llm_used", False),
        metadata={
            "matched_patterns": matched_patterns,
            "student_id": student_id,
            "message_length": len(user_message)
        }
    )


@router.get("/intents", response_model=List[Dict[str, Any]])
async def list_intents():
    """
    List all supported intents with descriptions and keywords.
    
    Useful for discovering what the chatbot can do.
    """
    return [
        {
            "name": intent_def.name,
            "description": intent_def.description,
            "action": intent_def.action,
            "keywords": intent_def.keywords
        }
        for intent_def in INTENTS.values()
    ]


@router.get("/status")
async def chat_status():
    """
    Get chatbot system status.
    
    Returns LLM availability and configuration.
    """
    llm_client = get_llm_client()
    
    return {
        "status": "operational",
        "llm_available": llm_client.is_available(),
        "llm_config": {
            "enabled": llm_client.config.enabled,
            "model": llm_client.config.model,
            "base_url": llm_client.config.base_url,
            "timeout": llm_client.config.timeout,
            "max_tokens": llm_client.config.max_tokens,
            "temperature": llm_client.config.temperature
        },
        "supported_intents": list(INTENTS.keys()),
        "intent_count": len(INTENTS)
    }


@router.get("/test/{student_id}")
async def test_chatbot(student_id: int):
    """
    Health check endpoint for testing.
    
    Args:
        student_id: Test student ID
        
    Returns:
        Basic health check response
    """
    # Test intent classification
    test_messages = [
        ("generate a workout", "generate_workout"),
        ("how tired am i", "check_fatigue"),
        ("why this exercise", "explain_plan"),
        ("hello", "general_chat"),
    ]
    
    results = []
    for message, expected_intent in test_messages:
        intent, confidence, _ = classify_intent(message)
        results.append({
            "message": message,
            "expected": expected_intent,
            "detected": intent,
            "confidence": round(confidence, 3),
            "correct": intent == expected_intent
        })
    
    return {
        "status": "healthy",
        "student_id": student_id,
        "classification_tests": results,
        "all_passed": all(r["correct"] for r in results)
    }
