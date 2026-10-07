"""
Intent classifier module.
Fast, rule-based intent classification with confidence scoring.
"""

from typing import Tuple, List
from .rules import match_intent
from .intents import INTENTS, get_intent_action


class IntentClassifier:
    """
    High-performance intent classifier using pattern matching.
    Replaces slow ML models with regex and keyword matching.
    """
    
    def __init__(self):
        self.intents = INTENTS
    
    def classify(self, text: str) -> Tuple[str, float, List[str]]:
        """
        Classify user text into an intent.
        
        Args:
            text: User message text
            
        Returns:
            Tuple of (intent_name, confidence_score, matched_patterns)
        """
        return match_intent(text)
    
    def classify_with_action(self, text: str) -> dict:
        """
        Classify text and return full intent information.
        
        Args:
            text: User message text
            
        Returns:
            Dictionary with intent, action, confidence, and patterns
        """
        intent_name, confidence, patterns = self.classify(text)
        action = get_intent_action(intent_name)
        
        return {
            "intent": intent_name,
            "action": action,
            "confidence": confidence,
            "matched_patterns": patterns,
            "description": self.intents[intent_name].description if intent_name in self.intents else ""
        }
    
    def get_supported_intents(self) -> List[dict]:
        """Get list of all supported intents with metadata."""
        return [
            {
                "name": intent.name,
                "description": intent.description,
                "action": intent.action,
                "keywords": intent.keywords
            }
            for intent in self.intents.values()
        ]


# Singleton instance for reuse
_classifier_instance = None


def get_classifier() -> IntentClassifier:
    """Get or create the singleton classifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = IntentClassifier()
    return _classifier_instance


def classify_intent(text: str) -> Tuple[str, float, List[str]]:
    """Convenience function to classify intent using singleton."""
    return get_classifier().classify(text)
