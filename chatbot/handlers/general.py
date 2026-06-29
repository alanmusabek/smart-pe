"""
Handler for general_chat intent.
Handles greetings, help requests, and general conversation with LLM.
"""

from typing import Dict, Any
from ..llm.responder import generate_llm_with_fallback
from ..llm.prompts import get_system_prompt


# Pre-defined responses for common greetings (fast path)
GREETING_RESPONSES = {
    "hello": "Hello! 👋 I'm your Smart PE AI assistant. How can I help you today? I can generate workouts, check your fatigue levels, explain your training plan, or answer any fitness questions!",
    "hi": "Hi there! 💪 Ready to crush your fitness goals? Let me know if you need a workout plan, want to check your recovery, or have any questions!",
    "hey": "Hey! 🏋️ What's up? I'm here to help with your training. Need a new workout, want to check how recovered you are, or just have a question?",
    "help": "I'd be happy to help! Here's what I can do:\n\n• **Generate Workouts** - Create personalized training plans\n• **Check Fatigue** - Analyze your muscle recovery status\n• **Explain Plans** - Tell you why specific exercises were chosen\n• **Record Feedback** - Log your workout completions and ratings\n• **Show Progress** - Display your stats and improvements\n• **Exercise Recommendations** - Suggest exercises for specific goals\n\nJust ask me anything!",
    "thanks": "You're welcome! 😊 Keep up the great work! Remember, consistency is key. Let me know if you need anything else!",
    "thank you": "You're very welcome! 💪 Your dedication is inspiring. Don't hesitate to reach out if you need help with your training!",
    "goodbye": "Goodbye! 👋 Keep crushing those goals! Come back anytime you need help with your workouts. You've got this! 🏆",
    "bye": "See you later! 💪 Stay strong and keep pushing forward. I'm always here when you need me!",
    "who are you": "I'm your Smart PE AI assistant! 🤖💪 I'm here to help you optimize your training by generating personalized workouts, analyzing your recovery, explaining exercise choices, and tracking your progress. Think of me as your 24/7 personal trainer and sports scientist combined!",
    "what can you do": "I'm your all-in-one fitness assistant! Here's my toolkit:\n\n🏋️ **Workout Generation** - Custom plans tailored to your goals\n📊 **Fatigue Analysis** - Know when to push and when to rest\n🧠 **Plan Explanations** - Understand the 'why' behind every exercise\n📈 **Progress Tracking** - See how far you've come\n💬 **Exercise Advice** - Get recommendations for any muscle group\n\nWhat would you like to tackle first?",
}


async def handle_general_chat(
    student_id: int,
    user_message: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Handle general_chat intent.
    
    Args:
        student_id: The student's ID
        user_message: Original user message
        use_llm: Whether to use LLM for response generation
        
    Returns:
        Response dictionary with action, message, and data
    """
    message_lower = user_message.lower().strip()
    
    # Check for quick greeting responses (fast path, no LLM needed)
    for greeting, response in GREETING_RESPONSES.items():
        if message_lower == greeting or message_lower.startswith(greeting + " ") or message_lower.endswith(" " + greeting):
            return {
                "action": "chat",
                "message": response,
                "data": {"greeting_detected": greeting},
                "llm_used": False
            }
    
    # For other messages, use LLM for dynamic response
    context_data = {
        "student_id": student_id,
        "message_type": "general_inquiry"
    }
    
    # Fallback template response
    fallback_message = (
        f"Thanks for your message! 😊 I'm here to help you with your fitness journey.\n\n"
        f"You said: \"{user_message}\"\n\n"
        f"I can help you with:\n"
        f"• Creating personalized workout plans\n"
        f"• Checking your muscle recovery status\n"
        f"• Explaining your training decisions\n"
        f"• Tracking your progress over time\n\n"
        f"What would you like to work on today? 💪"
    )
    
    # Generate LLM response or use fallback
    if use_llm:
        system_prompt = get_system_prompt("general_chat")
        message, llm_used = generate_llm_with_fallback(
            intent="general_chat",
            user_message=user_message,
            fallback_response=fallback_message,
            context_data=context_data,
            custom_system_prompt=system_prompt
        )
    else:
        message = fallback_message
        llm_used = False
    
    return {
        "action": "chat",
        "message": message,
        "data": {"conversation": True},
        "llm_used": llm_used
    }
