"""
Pattern matching rules for intent classification.
Uses regex and keyword matching for fast, accurate intent detection.
"""

import re
from typing import List, Tuple, Dict
from .intents import INTENTS, IntentDefinition


# Regex patterns for each intent (more precise than keywords alone)
INTENT_PATTERNS = {
    "generate_workout": [
        r"\b(generate|create|make|get|need)\s+(workout|plan|routine|session|exercise)",
        r"\b(workout|training|exercise)\s+plan",
        r"\b(today's|todays|today)\s+(workout|session|training)",
        r"\bnew\s+(workout|plan|routine)",
        r"\bwhat\s+(should|i|can)\s+(do|train|workout)\s+(today|now)",
    ],
    "check_fatigue": [
        r"\b(fatigue|tired|sore|ache|pain|recovery)\b",
        r"\b(how's|how is|check|status)\s+(my\s+)?(muscle|recovery|fatigue)",
        r"\b(am i|ready|should i)\s+(rest|recover|train|workout)",
        r"\b(muscle|body)\s+( sore|tired|aching|painful)",
        r"\b(recovery|rest)\s+(day|time|status|needed)",
    ],
    "explain_plan": [
        r"\bwhy\s+(did|does|is|are)\s+(you|the|this|ai)",
        r"\b(explain|reason|purpose|goal)\s+(this|that|the|my)",
        r"\b(choose|selected|picked)\s+(this|that|the)\s+(exercise|plan|workout)",
        r"\b(what's|whats|what is)\s+(the|a)\s+(reason|purpose|benefit|goal)",
        r"\b(target|focus)\s+(this|that|my)\s+(muscle|area|group)",
    ],
    "record_feedback": [
        r"\b(feedback|rate|rating|review|log)\b",
        r"\b(completed|finished|done)\s+(workout|exercise|session)",
        r"\b(too\s+)?(hard|easy|difficult|challenging)",
        r"\b(score|rating)\s+(of|is)\s+\d+",
        r"\b(i\s+)?(gave|give|submit)\s+feedback",
    ],
    "exercise_recommendation": [
        r"\b(recommend|suggest|advise)\s+(exercise|workout|movement)",
        r"\b(best|good|effective)\s+(exercise|workout)\s+(for|to)",
        r"\b(what|which)\s+(exercise|workout)\s+(for|should|to)",
        r"\b(exercise|workout)\s+for\s+(chest|legs|back|arms|shoulders|core|abs)",
        r"\b(how|what)\s+to\s+(train|work|target)\s+(my\s+)?\w+",
    ],
    "progress_check": [
        r"\b(progress|improvement|stats|statistics|history)\b",
        r"\b(how\s+(am|i|much)\s+(improved|doing|progressed))",
        r"\b(track|see|view|check)\s+(my\s+)?(progress|stats|history|improvement)",
        r"\b(personal|best|record|pr|pb)",
        r"\b(improved|better|stronger|faster)\s+(since|over|in)",
    ],
    "general_chat": [
        r"\b(hello|hi|hey|greetings|sup|yo)\b",
        r"\b(thanks|thank you|appreciate|grateful)\b",
        r"\b(goodbye|bye|see you|later)\b",
        r"\b(who are you|what are you|help|assist)\b",
        r"\b(how (are you|can you|do i|does this))",
        r"\b(what can you do|what do you do|your purpose)",
    ]
}


# Boost patterns that increase confidence when matched
BOOST_PATTERNS = {
    "generate_workout": [r"\bplease\b", r"\bnow\b", r"\btoday\b", r"\bimmediately\b"],
    "check_fatigue": [r"\bright now\b", r"\btoday\b", r"\bcurrently\b", r"\bat the moment\b"],
    "explain_plan": [r"\bexactly\b", r"\bspecifically\b", r"\bdetail\b"],
    "record_feedback": [r"\bjust\b", r"\bwanted to\b", r"\bquick\b"],
    "exercise_recommendation": [r"\bbest\b", r"\bmost effective\b", r"\btop\b"],
    "progress_check": [r"\boverall\b", r"\btotal\b", r"\ball time\b"],
    "general_chat": [r"\bplease\b", r"\bquickly\b", r"\bbriefly\b"],
}


def compile_patterns() -> Dict[str, List[re.Pattern]]:
    """Compile all regex patterns for efficiency."""
    compiled = {}
    for intent, patterns in INTENT_PATTERNS.items():
        compiled[intent] = [re.compile(p, re.IGNORECASE) for p in patterns]
    return compiled


def compile_boost_patterns() -> Dict[str, List[re.Pattern]]:
    """Compile boost patterns."""
    compiled = {}
    for intent, patterns in BOOST_PATTERNS.items():
        compiled[intent] = [re.compile(p, re.IGNORECASE) for p in patterns]
    return compiled


# Pre-compiled patterns for performance
COMPILED_PATTERNS = compile_patterns()
COMPILED_BOOST_PATTERNS = compile_boost_patterns()


def match_intent(text: str) -> Tuple[str, float, List[str]]:
    """
    Match user text to an intent using pattern matching.
    
    Args:
        text: User message text
        
    Returns:
        Tuple of (intent_name, confidence_score, list_of_matched_patterns)
    """
    text_lower = text.lower()
    scores = {}
    matched_patterns = {}
    
    # Check each intent's patterns
    for intent_name, patterns in COMPILED_PATTERNS.items():
        matches = []
        for pattern in patterns:
            if pattern.search(text):
                matches.append(pattern.pattern)
        
        if matches:
            # Base score: 0.7 + 0.1 per additional match (max 1.0)
            base_score = 0.7 + min(0.1 * (len(matches) - 1), 0.3)
            scores[intent_name] = base_score
            matched_patterns[intent_name] = matches
    
    # Apply boost patterns
    for intent_name, boost_patterns in COMPILED_BOOST_PATTERNS.items():
        if intent_name in scores:
            boost_count = sum(1 for p in boost_patterns if p.search(text))
            if boost_count > 0:
                # Add small boost (max 0.05)
                boost = min(0.02 * boost_count, 0.05)
                scores[intent_name] = min(scores[intent_name] + boost, 1.0)
    
    # If no patterns matched, use keyword fallback
    if not scores:
        scores = keyword_fallback(text_lower)
        if scores:
            matched_patterns = {k: ["keyword_match"] for k in scores.keys()}
    
    # Return best match
    if scores:
        best_intent = max(scores, key=scores.get)
        return best_intent, scores[best_intent], matched_patterns.get(best_intent, [])
    
    # Default to general_chat with low confidence
    return "general_chat", 0.3, ["default_fallback"]


def keyword_fallback(text_lower: str) -> Dict[str, float]:
    """
    Fallback to simple keyword matching if regex patterns don't match.
    
    Args:
        text_lower: Lowercased user text
        
    Returns:
        Dictionary of intent_name -> score
    """
    scores = {}
    
    for intent_name, intent_def in INTENTS.items():
        keyword_matches = 0
        for keyword in intent_def.keywords:
            if keyword in text_lower:
                keyword_matches += 1
        
        if keyword_matches > 0:
            # Score based on number of keyword matches
            scores[intent_name] = min(0.4 + (0.1 * keyword_matches), 0.6)
    
    return scores


def get_all_patterns() -> Dict[str, List[str]]:
    """Get all patterns as strings (for debugging/testing)."""
    return {
        intent: [p.pattern for p in patterns]
        for intent, patterns in COMPILED_PATTERNS.items()
    }
