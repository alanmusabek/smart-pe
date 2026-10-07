import pytest
from routers.chatbot import detect_intent


@pytest.mark.parametrize('text', [
    'Tell me about my workout',
    'How do you create a workout plan?',
    'Напиши короткое сообщение о занятиях',
    'Покажи мой план',
    'Show my latest workout plan',
    'I want to ask you a question',
])
def test_conversation_does_not_create_workouts(text):
    assert detect_intent(text)[0] != 'generate_workout'


@pytest.mark.parametrize('text', ['Create a workout plan', 'Please generate a new plan', 'Can you make a workout plan?', 'Составь мне план тренировок'])
def test_explicit_workout_request_is_recognized(text):
    assert detect_intent(text)[0] == 'generate_workout'
