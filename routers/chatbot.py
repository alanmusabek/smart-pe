"""
chatbot.py — FastAPI router for Smart PE AI Chatbot with LLM Integration
Features:
- Fast keyword-based intent detection (no slow ML models)
- Full database integration for real student data
- LLM-powered dynamic response generation (Ollama/OpenAI compatible)
- Multiple intents: workout generation, fatigue check, plan explanation, 
  feedback submission, exercise recommendations, progress tracking, general chat
- Fallback to template responses if LLM is unavailable
"""
import os
import re
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from auth import get_current_user
from feature_extractor import get_connection

# Optional LLM imports
try:
    from openai import OpenAI
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False
    OpenAI = None

router = APIRouter(prefix="/chat", tags=["Chatbot"])


# ==================== LLM CONFIGURATION ====================
LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")  # Ollama default
LLM_API_KEY = os.getenv("LLM_API_KEY", "ollama")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:0.5b")  # Changed to ultra-fast 0.5b model for instant responses
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "600"))  # Increased from 15s to 600s (10 minutes)
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "80"))  # Decreased from 150 to 80 for faster responses
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# Initialize LLM client if available and enabled
llm_client = None
if LLM_AVAILABLE and LLM_ENABLED:
    try:
        llm_client = OpenAI(
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            timeout=LLM_TIMEOUT
        )
        print(f"✅ LLM client initialized: {LLM_MODEL} at {LLM_BASE_URL}")
        print(f"   - Timeout: {LLM_TIMEOUT}s ({LLM_TIMEOUT // 60} min)")
        print(f"   - Max Tokens: {LLM_MAX_TOKENS} (optimized for speed)")
        print(f"   - Temperature: {LLM_TEMPERATURE}")
        print(f"   - Model: Ultra-fast qwen2.5:0.5b for instant chat responses")
    except Exception as e:
        print(f"⚠️  LLM client initialization failed: {e}. Falling back to template responses.")
        llm_client = None
else:
    if not LLM_AVAILABLE:
        print("⚠️  OpenAI library not installed. Install with: pip install openai")
    else:
        print("ℹ️  LLM disabled via environment variable. Using template responses.")


# ==================== REQUEST/RESPONSE SCHEMAS ====================
class ChatMessage(BaseModel):
    text: str
    context: Optional[Dict[str, Any]] = None  # Optional context like plan_id, exercise_id


class ChatResponse(BaseModel):
    intent: str
    confidence: float
    message: str
    action: str
    data: Optional[Dict[str, Any]] = None
    llm_used: bool = False


# ==================== INTENT DEFINITIONS ====================
INTENTS = {
    "generate_workout": {
        "keywords": [
            "generate", "create", "new plan", "new workout", "weekly plan",
            "workout plan", "exercise plan", "training plan", "give me",
            "i need", "want to", "make me", "build", "design",
            "план", "тренировк", "составь", "упражнен", "заняти",
            "неделю", "программ", "спорт", "фитнес", "нагрузк"
        ],
        "patterns": [
            r"(generate|create|make|build|design)\s*(a|my|the)?\s*(workout|plan|exercise|training)",
            r"(i\s*(need|want))\s*(a|some|new)?\s*(workout|plan|exercises?)",
            r"(give|get)\s*me\s*(a|my|the)?\s*(workout|plan)",
            r"what\s*(should|i\s*)?\s*(i\s*)?do\s*(today|this\s*week)?",
            r"(today|this\s*week)\s*(workout|plan|exercise)",
            r"(составь|создай|сделай|напиши)\s*(мне|)\s*(план|программ|тренировк)",
            r"(план|программа)\s*(тренировк|заняти|упражнен)",
            r"(хочу|нужно|надо)\s*(трениров|занимать|план)",
        ],
        "description": "User wants to create or get a new workout plan"
    },
    "check_fatigue": {
        "keywords": [
            "fatigue", "recovery", "sore", "soreness", "tired", "muscle",
            "recover", "rest", "ache", "pain", "hurt", "stiff", "exhausted",
            "how am i", "am i ready", "can i train", "should i rest"
        ],
        "patterns": [
            r"(how\s*(is|are|'s)?\s*my)\s*(recovery|fatigue|muscles?|condition)",
            r"(am\s*i\s*(ready|recovered|too\s*tired))",
            r"(check|show|tell\s*me)\s*(my\s*)?(recovery|fatigue|muscle)",
            r"(i\s*(feel|am))\s*(tired|sore|exhausted|aching|stiff)",
            r"(should\s*i\s*(rest|train|workout))",
        ],
        "description": "User wants to check their muscle fatigue or recovery status"
    },
    "explain_plan": {
        "keywords": [
            "why", "explain", "reason", "because", "chose", "chosen", "selected",
            "recommend", "recommendation", "logic", "understand", "purpose",
            "meaning", "what does", "how does"
        ],
        "patterns": [
            r"why\s*(did|does|is|are)\s*(you|the\s*ai|the\s*system)",
            r"(explain|tell\s*me)\s*(why|the\s*reason|how)",
            r"what\s*(is|was)\s*(the\s*)?(reason|logic|purpose)",
            r"how\s*(did|does)\s*(you|the\s*ai)\s*(choose|decide|select)",
            r"(this|that|these)\s*(plan|exercise|workout)\s*(why|reason)",
        ],
        "description": "User wants to understand why the AI chose specific exercises or plans"
    },
    "record_feedback": {
        "keywords": [
            "feedback", "rate", "rating", "review", "comment", "opinion",
            "liked", "disliked", "hate", "love", "good", "bad", "great",
            "terrible", "awesome", "awful", "submit", "log", "report"
        ],
        "patterns": [
            r"(i\s*(liked|loved|hated|disliked|enjoyed))",
            r"(this\s*was|it\s*was)\s*(great|good|bad|terrible|awesome|awful)",
            r"(submit|send|give|leave)\s*(my\s*)?(feedback|review|rating)",
            r"(rate|review)\s*(this|the|my)\s*(workout|plan|exercise)",
            r"(want|need)\s*(to\s*)?(submit|give|log)\s*feedback",
        ],
        "description": "User wants to submit feedback, rate a workout, or log an exercise"
    },
    "exercise_recommendation": {
        "keywords": [
            "recommend", "suggest", "best", "good", "should i do", "what exercise",
            "which exercise", "help me", "need help", "advice", "tips",
            "improve", "strengthen", "target", "focus on", "exercises for"
        ],
        "patterns": [
            r"(recommend|suggest)\s*(me|some)?\s*(exercises?|workouts?)",
            r"(what|which)\s*(exercises?|workouts?)\s*(should|i\s*)?\s*(do|try)",
            r"(i\s*(need|want))\s*(help|advice|tips)\s*(with|for)",
            r"(how\s*can|i\s*)?\s*(improve|strengthen|target)\s*(my\s*)?",
            r"(best|good)\s*(exercises?|workouts?)\s*(for|to)",
            r"exercises\s*(for|to)\s*(chest|legs|arms|back|core|cardio)",
            r"improve\s*(my\s*)?(chest|legs|arms|back|core|strength)",
        ],
        "description": "User wants exercise recommendations or advice"
    },
    "progress_check": {
        "keywords": [
            "progress", "improvement", "history", "stats", "statistics",
            "performance", "track", "tracking", "compare", "before", "after",
            "how much", "how many", "my record", "personal best", "pb",
            "my progress", "track progress", "track improvement"
        ],
        "patterns": [
            r"(how\s*(is|am|i'm)\s*my)\s*(progress|improvement|performance)",
            r"(show|tell)\s*(me\s*)?(my\s*)?(progress|history|stats|statistics)",
            r"(what\s*(is|was|are|were)\s*(my\s*)?)?(record|best|pb|personal\s*best)",
            r"(track|tracking)\s*(my\s*)?(progress|performance|improvement)",
            r"(compare|before|after)\s*(my\s*)?(performance|results)",
            r"track\s*(my\s*)?progress",
            r"track\s*(my\s*)?improvement",
            r"my\s*progress",
            r"my\s*improvement",
        ],
        "description": "User wants to check their progress or performance history"
    },
    "general_chat": {
        "keywords": [
            "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
            "thanks", "thank you", "bye", "goodbye", "see you", "help",
            "what can you", "who are you", "your name", "features", "capabilities"
        ],
        "patterns": [
            r"^(hi|hello|hey|greetings)",
            r"(good\s*(morning|afternoon|evening))",
            r"(thank\s*(you|s)|thanks)",
            r"(bye|goodbye|see\s*you|later)",
            r"(what\s*(can|do)\s*(you|u)\s*do)",
            r"(who\s*(are|is)\s*(you|u|this))",
            r"(help\s*(me|please))",
        ],
        "description": "General greeting, farewell, or app-related questions"
    }
}

INTENT_PRIORITY = [
    "generate_workout",
    "check_fatigue", 
    "explain_plan",
    "record_feedback",
    "exercise_recommendation",
    "progress_check",
    "general_chat"
]


# ==================== FAST INTENT DETECTION ====================
def detect_intent(message: str) -> tuple[str, float]:
    """
    Fast keyword and pattern-based intent detection.
    Returns (intent_name, confidence_score)
    """
    message_lower = message.lower().strip()
    
    scores = {}
    
    for intent_name, intent_data in INTENTS.items():
        score = 0.0
        
        # Check keywords (each match adds 0.1)
        for keyword in intent_data["keywords"]:
            if keyword in message_lower:
                score += 0.1
        
        # Check regex patterns (each match adds 0.3)
        for pattern in intent_data["patterns"]:
            if re.search(pattern, message_lower):
                score += 0.3
        
        if score > 0:
            # Cap at 0.95 to leave room for uncertainty
            scores[intent_name] = min(0.95, score)
    
    if not scores:
        return "general_chat", 0.5
    
    # Return highest scoring intent
    best_intent = max(scores, key=scores.get)
    return best_intent, round(scores[best_intent], 3)


# ==================== DATABASE HELPERS ====================
def get_student_profile(student_id: int) -> dict:
    """Fetch student profile and physical data from database."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT s.student_id, s.age, s.gender,
                   hp.medical_group_id, hp.height_cm, hp.weight_kg,
                   hp.cooper_meters, hp.push_ups, hp.pull_ups,
                   hp.flexibility_cm, hp.sit_ups, hp.jump_forward,
                   a."BMI", a.strength_score, a.endurance_score, a.flexibility_score
            FROM students s
            JOIN students_health_profiles hp ON hp.student_id = s.student_id
            LEFT JOIN students_physical_readiness_assessments a ON a.health_profile_id = hp.health_profile_id
            WHERE s.student_id = %s
            LIMIT 1
        """, (student_id,))
        
        row = cur.fetchone()
        if not row:
            return None
            
        return {
            "student_id": row[0],
            "age": row[1],
            "gender": row[2],
            "medical_group_id": row[3],
            "height_cm": row[4],
            "weight_kg": row[5],
            "cooper_meters": row[6],
            "push_ups": row[7],
            "pull_ups": row[8],
            "flexibility_cm": row[9],
            "sit_ups": row[10],
            "jump_forward": row[11],
            "bmi": float(row[12]) if row[12] else None,
            "strength_score": float(row[13]) if row[13] else None,
            "endurance_score": float(row[14]) if row[14] else None,
            "flexibility_score": float(row[15]) if row[15] else None,
        }
    finally:
        cur.close()
        conn.close()


def get_muscle_fatigue(student_id: int) -> dict:
    """Get current muscle fatigue/recovery status for student."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT mg.muscle_name, mf.recovery_left, mf.status, mf.date
            FROM muscle_fatigue mf
            JOIN assigned_exercise_muscle_group aemg 
                ON aemg.assigned_exercise_muscle_group_id = mf.assigned_exercise_muscle_group_id
            JOIN muscle_group mg ON mg.muscle_group_id = aemg.muscle_group_id
            WHERE mf.student_id = %s AND mf.status = 'ACTIVE'
            ORDER BY mf.date DESC
        """, (student_id,))
        
        rows = cur.fetchall()
        if not rows:
            return {"status": "No active fatigue data", "muscles": {}}
        
        muscles = {}
        for row in rows:
            muscle_name = row[0]
            recovery_left = float(row[1]) if row[1] else 0
            status = row[2]
            
            if muscle_name not in muscles or muscles[muscle_name]["recovery_left_hours"] < recovery_left:
                muscles[muscle_name] = {
                    "recovery_left_hours": recovery_left,
                    "status": status,
                    "last_updated": str(row[3]) if row[3] else None
                }
        
        return {"status": "active", "muscles": muscles}
    finally:
        cur.close()
        conn.close()


def get_latest_plan(student_id: int) -> Optional[dict]:
    """Get the most recent workout plan for a student."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT wp.workout_plan_id, wp.date, wp.workout_status, wp.satisfaction,
                   COUNT(ae.assigned_exercise_id) as exercise_count
            FROM workout_plan wp
            LEFT JOIN assigned_exercise ae ON ae.workout_plan_id = wp.workout_plan_id
            WHERE wp.student_id = %s
            GROUP BY wp.workout_plan_id, wp.date, wp.workout_status, wp.satisfaction
            ORDER BY wp.date DESC
            LIMIT 1
        """, (student_id,))
        
        row = cur.fetchone()
        if not row:
            return None
        
        return {
            "plan_id": row[0],
            "date": str(row[1]),
            "status": row[2],
            "satisfaction": row[3],
            "exercise_count": row[4]
        }
    finally:
        cur.close()
        conn.close()


def get_plan_exercises(plan_id: int) -> List[dict]:
    """Get exercises in a specific plan."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT e.exercise_id, e.exercise_name, e.difficulty, c.category_name,
                   ae.recommended_sets, ae.recommended_reps, ae.slot_type,
                   ae.day_of_week, ae.predicted_score
            FROM assigned_exercise ae
            JOIN exercises e ON e.exercise_id = ae.exercise_id
            JOIN exercise_categories c ON c.category_id = e.category_id
            WHERE ae.workout_plan_id = %s
            ORDER BY ae.day_of_week, ae.order_in_session
        """, (plan_id,))
        
        rows = cur.fetchall()
        return [{
            "exercise_id": r[0],
            "name": r[1],
            "difficulty": r[2],
            "category": r[3],
            "sets": r[4],
            "reps": r[5],
            "slot_type": r[6],
            "day": r[7],
            "predicted_score": float(r[8]) if r[8] else None
        } for r in rows]
    finally:
        cur.close()
        conn.close()


def get_interaction_history(student_id: int, limit: int = 10) -> List[dict]:
    """Get recent interaction history for a student."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            SELECT e.exercise_name, saei.completed, saei.perceived_difficulty,
                   saei.actually_sets, saei.actually_reps, saei.interaction_date,
                   saei.feedback_notes
            FROM student_assigned_exercise_interaction saei
            JOIN assigned_exercise ae ON ae.assigned_exercise_id = saei.assigned_exercise_id
            JOIN exercises e ON e.exercise_id = ae.exercise_id
            WHERE saei.student_id = %s
            ORDER BY saei.interaction_date DESC
            LIMIT %s
        """, (student_id, limit))
        
        rows = cur.fetchall()
        return [{
            "exercise": r[0],
            "completed": r[1],
            "perceived_difficulty": r[2],
            "actual_sets": r[3],
            "actual_reps": r[4],
            "date": str(r[5]),
            "feedback": r[6]
        } for r in rows]
    finally:
        cur.close()
        conn.close()


def get_progress_stats(student_id: int) -> dict:
    """Get progress statistics for a student."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Overall completion rate
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN completed THEN 1 ELSE 0 END) as completed_count,
                AVG(CASE WHEN completed THEN 1.0 ELSE 0.0 END) as completion_rate
            FROM student_assigned_exercise_interaction saei
            WHERE saei.student_id = %s
        """, (student_id,))
        
        row = cur.fetchone()
        total = row[0] or 0
        completed = row[1] or 0
        completion_rate = float(row[2]) if row[2] else 0
        
        # Average perceived difficulty
        cur.execute("""
            SELECT AVG(CASE 
                WHEN perceived_difficulty = 'Very Easy' THEN 1
                WHEN perceived_difficulty = 'Easy' THEN 2
                WHEN perceived_difficulty = 'Normal' THEN 3
                WHEN perceived_difficulty = 'Hard' THEN 4
                WHEN perceived_difficulty = 'Very Hard' THEN 5
                ELSE NULL END)
            FROM student_assigned_exercise_interaction
            WHERE student_id = %s AND perceived_difficulty IS NOT NULL
        """, (student_id,))
        
        avg_diff = cur.fetchone()[0]
        
        # Plans completed
        cur.execute("""
            SELECT COUNT(*) FROM workout_plan
            WHERE student_id = %s AND workout_status = 'COMPLETED'
        """, (student_id,))
        
        plans_completed = cur.fetchone()[0] or 0
        
        return {
            "total_interactions": total,
            "completed_exercises": completed,
            "completion_rate": round(completion_rate, 3),
            "avg_perceived_difficulty": round(float(avg_diff), 2) if avg_diff else None,
            "plans_completed": plans_completed,
            "difficulty_scale": "1=Very Easy, 5=Very Hard"
        }
    finally:
        cur.close()
        conn.close()


def get_exercise_recommendations(student_id: int, category: str = None, limit: int = 5) -> List[dict]:
    """Get exercise recommendations based on student profile and history."""
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Get student's fitness level
        cur.execute("""
            SELECT (COALESCE(a.strength_score, 3) + COALESCE(a.endurance_score, 3) + COALESCE(a.flexibility_score, 3)) / 3 as fitness_level,
                   hp.medical_group_id
            FROM students s
            JOIN students_health_profiles hp ON hp.student_id = s.student_id
            LEFT JOIN students_physical_readiness_assessments a ON a.health_profile_id = hp.health_profile_id
            WHERE s.student_id = %s
            LIMIT 1
        """, (student_id,))
        
        profile = cur.fetchone()
        if not profile:
            return []
        
        fitness_level = float(profile[0]) if profile[0] else 3
        medical_group = profile[1]
        
        # Max allowed difficulty based on medical group
        max_difficulty = {1: 5, 2: 3, 3: 2}.get(medical_group, 5)
        
        # Get recommended exercises (avoid recently completed ones)
        query = """
            SELECT e.exercise_id, e.exercise_name, e.difficulty, c.category_name,
                   e.recommended_sets, e.recommended_reps
            FROM exercises e
            JOIN exercise_categories c ON c.category_id = e.category_id
            WHERE CASE e.difficulty
                WHEN 'low' THEN 1
                WHEN 'medium' THEN 3
                WHEN 'high' THEN 5
                ELSE 3
            END <= %s
              AND e.exercise_id NOT IN (
                  SELECT ae.exercise_id
                  FROM student_assigned_exercise_interaction saei
                  JOIN assigned_exercise ae ON ae.assigned_exercise_id = saei.assigned_exercise_id
                  WHERE saei.student_id = %s
                  ORDER BY saei.interaction_date DESC
                  LIMIT 10
              )
        """
        params = [max_difficulty, student_id]
        
        if category:
            query += " AND c.category_name ILIKE %s"
            params.append(f"%{category}%")
        
        query += " ORDER BY e.difficulty ASC LIMIT %s"
        params.append(limit)
        
        cur.execute(query, params)
        rows = cur.fetchall()
        
        return [{
            "exercise_id": r[0],
            "name": r[1],
            "difficulty": r[2],
            "category": r[3],
            "recommended_sets": r[4],
            "recommended_reps": r[5]
        } for r in rows]
    finally:
        cur.close()
        conn.close()


# ==================== LLM RESPONSE GENERATION ====================
def generate_llm_response(system_prompt: str, user_prompt: str, context_data: dict = None) -> tuple[str, bool]:
    """
    Generate a dynamic response using the LLM with streaming support.
    Returns (response_text, llm_used_flag)
    
    Falls back to None if LLM is unavailable, so caller can use template response.
    Includes detailed console debugging to track the response generation process.
    """
    import time
    
    if not llm_client:
        print("⚠️  LLM client not available. Using template response.")
        return None, False
    
    start_time = time.time()
    
    try:
        # Build enhanced prompt with context data if available
        full_user_prompt = user_prompt
        if context_data:
            full_user_prompt += f"\n\nContext Data:\n{context_data}"
        
        # Log request details
        print("\n" + "="*80)
        print("🤖 LLM REQUEST STARTED")
        print("="*80)
        print(f"⏰ Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📦 Model: {LLM_MODEL}")
        print(f"🌡️  Temperature: {LLM_TEMPERATURE}")
        print(f"🔢 Max Tokens: {LLM_MAX_TOKENS}")
        print(f"⏳ Timeout: {LLM_TIMEOUT}s")
        print("-"*80)
        print("📝 SYSTEM PROMPT:")
        print(system_prompt[:200] + ("..." if len(system_prompt) > 200 else ""))
        print("-"*80)
        print("👤 USER PROMPT:")
        print(user_prompt[:200] + ("..." if len(user_prompt) > 200 else ""))
        if context_data:
            print("-"*80)
            print("📊 CONTEXT DATA:")
            print(str(context_data)[:300] + ("..." if len(str(context_data)) > 300 else ""))
        print("-"*80)
        print("⏳ Waiting for LLM response...")
        
        # Create completion with streaming enabled
        # Note: timeout is set in client initialization, not here
        stream = llm_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_user_prompt}
            ],
            temperature=LLM_TEMPERATURE,
            max_tokens=LLM_MAX_TOKENS,
            stream=True  # Enable streaming for faster perceived response
        )
        
        # Collect streamed chunks
        response_chunks = []
        chunk_count = 0
        first_chunk_time = None
        
        print("📡 Receiving stream...")
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    content = delta.content
                    response_chunks.append(content)
                    chunk_count += 1
                    
                    # Log first chunk timing
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                        time_to_first = first_chunk_time - start_time
                        print(f"✨ First token received in {time_to_first:.2f}s")
                    
                    # Log progress every 10 chunks
                    if chunk_count % 10 == 0:
                        elapsed = time.time() - start_time
                        print(f"   Chunk #{chunk_count}, Elapsed: {elapsed:.2f}s, Content: '{content.strip()[:50]}...'")
        
        # Assemble final response
        response_text = "".join(response_chunks).strip()
        end_time = time.time()
        total_time = end_time - start_time
        
        # Log response details
        print("-"*80)
        print("✅ LLM RESPONSE COMPLETED")
        print("="*80)
        print(f"⏱️  Total Time: {total_time:.2f}s")
        print(f"📊 Chunks Received: {chunk_count}")
        print(f"📝 Response Length: {len(response_text)} characters")
        print(f"🔤 Tokens/sec (approx): {chunk_count / total_time:.1f}" if total_time > 0 else "")
        print("-"*80)
        print("💬 GENERATED RESPONSE:")
        print(response_text[:500] + ("..." if len(response_text) > 500 else ""))
        print("="*80 + "\n")
        
        return response_text, True
        
    except Exception as e:
        end_time = time.time()
        elapsed = end_time - start_time
        print(f"\n❌ LLM GENERATION ERROR after {elapsed:.2f}s:")
        print(f"   Error Type: {type(e).__name__}")
        print(f"   Error Message: {str(e)}")
        print("="*80 + "\n")
        return None, False


# ==================== ACTION EXECUTORS ====================
def execute_generate_workout(student_id: int, message: str) -> dict:
    """Generate a new workout plan for the student using LLM."""
    from plan_assembler import generate_plan
    
    try:
        # Generate actual plan using existing plan_assembler
        weekly_plan = generate_plan(student_id=student_id, save_to_db=True)
        
        # Get summary
        total_exercises = sum(len(day.get("exercises", [])) for day in weekly_plan.get("days", []))
        
        # Prepare context for LLM
        profile = get_student_profile(student_id)
        context_data = {
            "student_profile": profile,
            "weekly_plan_summary": {
                "total_exercises": total_exercises,
                "days_count": len(weekly_plan.get("days", []))
            }
        }
        
        # Use LLM to generate personalized response if available
        system_prompt = """You are an expert, encouraging personal trainer AI assistant. 
Your role is to explain workout plans in a motivating, clear, and personalized way.
Focus on:
- Highlighting how the plan matches the student's fitness level
- Explaining the benefits of the exercises chosen
- Encouraging the student to stay consistent
- Mentioning safety considerations based on their medical group
Keep responses concise (3-5 sentences), friendly, and actionable."""

        user_prompt = f"""The student said: "{message}"
I've just generated a personalized weekly workout plan with {total_exercises} exercises across {len(weekly_plan.get("days", []))} days.

Student Profile:
- Fitness Level: {(profile.get('strength_score', 0) + profile.get('endurance_score', 0) + profile.get('flexibility_score', 0)) / 3 if profile and profile.get('strength_score') else 3:.1f}/5
- Medical Group: {profile.get('medical_group_id', 'N/A') if profile else 'N/A'}
- BMI: {profile.get('bmi', 'N/A')}

Please generate a motivating, personalized introduction to their new workout plan."""

        llm_response, llm_used = generate_llm_response(system_prompt, user_prompt, str(context_data))
        
        if llm_used and llm_response:
            response_message = llm_response
        else:
            # Fallback template
            response_message = (f"Great news! I've created a personalized weekly workout plan for you with {total_exercises} exercises. "
                              f"The plan is tailored to your fitness level and takes into account your medical group and any injury considerations. "
                              f"You can view the full plan in your dashboard or ask me to explain any specific exercises!")
        
        return {
            "action": "plan_generated",
            "message": response_message,
            "data": {
                "weekly_plan": weekly_plan,
                "total_exercises": total_exercises
            },
            "llm_used": llm_used
        }
    except Exception as e:
        return {
            "action": "error",
            "message": f"I encountered an issue generating your plan: {str(e)}. Please try again or contact support.",
            "data": None,
            "llm_used": False
        }



def execute_check_fatigue(student_id: int, message: str) -> dict:
    """Check and report muscle fatigue status using LLM analysis."""
    fatigue_data = get_muscle_fatigue(student_id)
    
    # Use LLM to analyze fatigue data if available
    system_prompt = """You are an analytical sports scientist AI assistant.
Your role is to analyze muscle recovery data and provide actionable, friendly advice.
Focus on:
- Clear explanation of recovery status for each muscle group
- Specific recommendations for what to train or avoid
- Encouraging tone while prioritizing safety
Keep responses concise (4-6 sentences)."""

    user_prompt = f"""The student asked: "{message}"
Here is their current muscle fatigue data: {fatigue_data}

Please provide a brief, friendly analysis of their recovery status and specific recommendations for today's training."""

    llm_response, llm_used = generate_llm_response(system_prompt, user_prompt, str(fatigue_data))
    
    if fatigue_data.get("status") == "No active fatigue data":
        if llm_used and llm_response:
            response_message = llm_response
        else:
            response_message = "Great news! You have no active muscle fatigue recorded. Your muscles appear to be recovered and ready for training! Remember to listen to your body and stay hydrated."
        
        return {
            "action": "show_fatigue",
            "message": response_message,
            "data": fatigue_data,
            "llm_used": llm_used
        }
    
    muscles = fatigue_data.get("muscles", {})
    if not muscles:
        return {
            "action": "show_fatigue",
            "message": "No fatigue data available. Make sure to log your workouts so I can track your recovery!",
            "data": fatigue_data
        }
    
    # Analyze fatigue levels
    fatigued_muscles = []
    recovering_muscles = []
    ready_muscles = []
    
    for muscle, data in muscles.items():
        recovery_hours = data.get("recovery_left_hours", 0)
        if recovery_hours > 48:
            fatigued_muscles.append(muscle)
        elif recovery_hours > 24:
            recovering_muscles.append(muscle)
        else:
            ready_muscles.append(muscle)
    
    message_parts = ["📊 Here's your current muscle recovery status:\n\n"]
    
    if fatigued_muscles:
        message_parts.append(f"⚠️ **Still Fatigued**: {', '.join(fatigued_muscles)}\n")
        message_parts.append("   These muscles need more rest. Avoid intense training targeting these areas.\n\n")
    
    if recovering_muscles:
        message_parts.append(f"🔄 **Recovering**: {', '.join(recovering_muscles)}\n")
        message_parts.append("   These are making good progress. Light activity is okay.\n\n")
    
    if ready_muscles:
        message_parts.append(f"✅ **Ready to Train**: {', '.join(ready_muscles)}\n")
        message_parts.append("   These muscles are recovered and ready for work!\n\n")
    
    message_parts.append("💡 **Recommendation**: ")
    if fatigued_muscles:
        message_parts.append("Focus on upper body or cardio today, or take an active recovery day.")
    else:
        message_parts.append("You're looking good for a full workout!")
    
    return {
        "action": "show_fatigue",
        "message": "".join(message_parts),
        "data": fatigue_data
    }


def execute_explain_plan(student_id: int, message: str, context: dict = None) -> dict:
    """Explain why certain exercises or plans were chosen using LLM."""
    plan_id = context.get("plan_id") if context else None
    
    # Get latest plan if none specified
    if not plan_id:
        latest_plan = get_latest_plan(student_id)
        if latest_plan:
            plan_id = latest_plan["plan_id"]
    
    if not plan_id:
        return {
            "action": "chat",
            "message": "I couldn't find a recent plan to explain. Would you like me to generate a new workout plan first?",
            "data": None,
            "llm_used": False
        }
    
    exercises = get_plan_exercises(plan_id)
    profile = get_student_profile(student_id)
    
    if not exercises:
        return {
            "action": "chat",
            "message": "This plan doesn't have any exercises recorded. Let me generate a fresh plan for you!",
            "data": None,
            "llm_used": False
        }
    
    # Use LLM to generate personalized explanation
    system_prompt = """You are an insightful AI coach specializing in exercise science.
Your role is to explain exercise selection in a clear, educational way.
Focus on:
- Connecting exercises to the student's specific goals and profile
- Explaining the science behind exercise choices
- Highlighting safety and progression considerations
Keep responses concise (5-7 sentences), encouraging, and informative."""

    context_data = {
        "profile": profile,
        "exercises": exercises[:5],  # Limit to first 5 for context window
        "plan_id": plan_id
    }

    user_prompt = f"""The student asked: "{message}"
Here is their profile: {profile}
Here are the exercises in their plan: {exercises[:5]}

Please explain why these specific exercises were chosen for this student, considering their fitness level, medical group, and training history."""

    llm_response, llm_used = generate_llm_response(system_prompt, user_prompt, str(context_data))
    
    if llm_used and llm_response:
        response_message = llm_response
    else:
        # Fallback template
        fitness_level = (profile.get("strength_score", 0) + 
                        profile.get("endurance_score", 0) + 
                        profile.get("flexibility_score", 0)) / 3 if profile and profile.get("strength_score") else 3
        
        response_message = (f"Here's why I chose these exercises for you:\n\n"
                          f"Your Profile: Fitness Level {fitness_level:.1f}/5, Medical Group {profile.get('medical_group_id', 'N/A') if profile else 'N/A'}\n\n"
                          f"Each exercise was selected based on:\n"
                          f"1. Your current fitness level and capabilities\n"
                          f"2. Medical group restrictions and safety\n"
                          f"3. Muscle balance and injury prevention\n"
                          f"4. Your previous workout history and preferences")
    
    return {
        "action": "explain",
        "message": response_message,
        "data": {
            "plan_id": plan_id,
            "exercises": exercises,
            "profile_summary": profile
        },
        "llm_used": llm_used
    }


def execute_record_feedback(student_id: int, message: str, context: dict = None) -> dict:
    """Process and record user feedback."""
    # Try to extract sentiment from message
    positive_words = ["great", "good", "awesome", "love", "liked", "excellent", "amazing", "perfect"]
    negative_words = ["bad", "terrible", "hate", "disliked", "awful", "horrible", "worst", "poor"]
    
    message_lower = message.lower()
    sentiment = "neutral"
    if any(word in message_lower for word in positive_words):
        sentiment = "positive"
    elif any(word in message_lower for word in negative_words):
        sentiment = "negative"
    
    # If there's a plan_id in context, update the plan satisfaction
    if context and context.get("plan_id"):
        conn = get_connection()
        cur = conn.cursor()
        try:
            satisfaction = "Liked" if sentiment == "positive" else ("Disliked" if sentiment == "negative" else None)
            if satisfaction:
                cur.execute("""
                    UPDATE workout_plan SET satisfaction = %s
                    WHERE workout_plan_id = %s AND student_id = %s
                """, (satisfaction, context["plan_id"], student_id))
                conn.commit()
        finally:
            cur.close()
            conn.close()
    
    return {
        "action": "feedback_recorded",
        "message": f"✅ Thank you for your feedback! I've recorded your response as {sentiment}. "
                  f"Your input helps me personalize future workouts specifically for you. "
                  f"Is there anything else you'd like to share or adjust?",
        "data": {
            "sentiment": sentiment,
            "recorded": True
        }
    }


def execute_exercise_recommendation(student_id: int, message: str) -> dict:
    """Provide exercise recommendations."""
    # Try to extract category preference from message
    category = None
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["chest", "push", "bench"]):
        category = "Strength"  # Will filter differently
    elif any(word in message_lower for word in ["cardio", "running", "endurance"]):
        category = "Cardio"
    elif any(word in message_lower for word in ["core", "abs", "plank"]):
        category = "Core"
    elif any(word in message_lower for word in ["stretch", "flexibility", "warmup"]):
        category = "Stretching"
    
    recommendations = get_exercise_recommendations(student_id, category, limit=5)
    
    if not recommendations:
        return {
            "action": "recommendations",
            "message": "I couldn't find specific recommendations at this time. Let me generate a full workout plan for you instead!",
            "data": None
        }
    
    message_parts = ["💪 Here are some exercises I recommend for you:\n\n"]
    
    for i, ex in enumerate(recommendations, 1):
        message_parts.append(f"{i}. **{ex['name']}**\n")
        message_parts.append(f"   Category: {ex['category']} | Difficulty: {ex['difficulty']}/5\n")
        message_parts.append(f"   Recommended: {ex['recommended_sets']} sets × {ex['recommended_reps']} reps\n\n")
    
    message_parts.append("💡 Want me to add these to a full workout plan? Just ask!")
    
    return {
        "action": "recommendations",
        "message": "".join(message_parts),
        "data": {
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    }


def execute_progress_check(student_id: int, message: str) -> dict:
    """Check and report user's progress statistics."""
    stats = get_progress_stats(student_id)
    history = get_interaction_history(student_id, limit=5)
    
    if stats["total_interactions"] == 0:
        return {
            "action": "progress",
            "message": "📊 I don't have enough data to show your progress yet. Complete some workouts and I'll start tracking your improvements!",
            "data": stats
        }
    
    message_parts = ["📈 Here's your progress summary:\n\n"]
    
    message_parts.append(f"✅ **Completion Rate**: {stats['completion_rate']*100:.1f}%\n")
    message_parts.append(f"   ({stats['completed_exercises']}/{stats['total_interactions']} exercises completed)\n\n")
    
    message_parts.append(f"🏆 **Plans Completed**: {stats['plans_completed']}\n\n")
    
    if stats["avg_perceived_difficulty"]:
        diff_label = {
            1: "Very Easy", 2: "Easy", 3: "Normal", 
            4: "Hard", 5: "Very Hard"
        }.get(round(stats["avg_perceived_difficulty"]), "Normal")
        message_parts.append(f"💪 **Average Difficulty**: {diff_label} ({stats['avg_perceived_difficulty']}/5)\n\n")
    
    if history:
        message_parts.append("🕐 **Recent Activity**:\n")
        for h in history[:3]:
            status = "✅" if h["completed"] else "⏭️"
            message_parts.append(f"   {status} {h['exercise']} - {h['date']}\n")
    
    return {
        "action": "progress",
        "message": "".join(message_parts),
        "data": {
            "stats": stats,
            "recent_history": history
        }
    }


def execute_general_chat(student_id: int, message: str) -> dict:
    """Handle general greetings and questions using LLM."""
    message_lower = message.lower()
    
    # Use LLM for dynamic responses when appropriate
    system_prompt = """You are a friendly, helpful Smart PE AI assistant.
Your role is to engage students in conversation about their fitness journey.
Focus on:
- Being warm, encouraging, and supportive
- Providing clear information about your capabilities
- Guiding students toward actionable fitness goals
Keep responses concise (3-5 sentences), conversational, and helpful."""

    profile = get_student_profile(student_id)
    context_data = {"profile": profile, "message": message}

    user_prompt = f"""The student said: "{message}"
Student profile: {profile}

Respond appropriately - whether it's a greeting, thank you, help request, farewell, or general question.
If they're asking what you can do, briefly mention: workout generation, fatigue checking, progress tracking, 
exercise explanations, feedback submission, and exercise recommendations."""

    llm_response, llm_used = generate_llm_response(system_prompt, user_prompt, str(context_data))
    
    # For simple greetings/thanks/farewells, still use fast templates if LLM not needed
    if not llm_used or not llm_response:
        # Greeting responses
        if any(greeting in message_lower for greeting in ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]):
            return {
                "action": "chat",
                "message": "Hello! I'm your Smart PE AI assistant. I can help you generate personalized workout plans, "
                          "check muscle fatigue and recovery, track progress and stats, explain why exercises were chosen, "
                          "submit feedback on workouts, and get exercise recommendations. What would you like to do today?",
                "data": None,
                "llm_used": False
            }
        
        # Thanks responses
        if any(word in message_lower for word in ["thank", "thanks", "appreciate"]):
            return {
                "action": "chat",
                "message": "You're welcome! I'm here to help you achieve your fitness goals. "
                          "Feel free to ask me anything about your workouts, progress, or recovery!",
                "data": None,
                "llm_used": False
            }
        
        # Farewell
        if any(word in message_lower for word in ["bye", "goodbye", "see you", "later"]):
            return {
                "action": "chat",
                "message": "Take care! Remember to stay consistent with your workouts and listen to your body. "
                          "Come back anytime you need help with your fitness journey!",
                "data": None,
                "llm_used": False
            }
        
        # Default response
        return {
            "action": "chat",
            "message": "Hi there! I'm your Smart PE AI assistant. I can help you generate workouts, check fatigue, "
                      "track progress, explain exercise choices, submit feedback, and recommend exercises. "
                      "What would you like to do today?",
            "data": None,
            "llm_used": False
        }
    
    return {
        "action": "chat",
        "message": llm_response,
        "data": None,
        "llm_used": True
    }


# ==================== MAIN CHAT ENDPOINT ====================
@router.post("/", response_model=ChatResponse)
def chat(message: ChatMessage, user: dict = Depends(get_current_user)):
    """
    Main chat endpoint with LLM-powered dynamic responses.
    
    Features:
    - Instant intent detection (keyword-based, milliseconds)
    - LLM-powered personalized response generation with streaming
    - Full database integration for real student data
    - Multiple intent support (7 intents)
    - Graceful fallback to templates if LLM unavailable
    - Configurable via environment variables
    - Detailed console debugging for monitoring LLM responses
    
    Environment Variables:
    - LLM_ENABLED: Enable/disable LLM (default: true)
    - LLM_BASE_URL: LLM API endpoint (default: http://localhost:11434/v1 for Ollama)
    - LLM_MODEL: Model name (default: qwen2.5:3b)
    - LLM_TIMEOUT: Request timeout in seconds (default: 600 = 10 minutes)
    - LLM_MAX_TOKENS: Max response tokens (default: 150)
    - LLM_TEMPERATURE: Response creativity (default: 0.7)
    """
    if not message.text or not message.text.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Get student_id from user (must be a student)
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="Chatbot is currently available for students only")
    
    student_id = user.get("student_id")
    if not student_id:
        raise HTTPException(status_code=400, detail="Student ID not found in user profile")
    
    # Fast intent detection (milliseconds, not seconds)
    intent, confidence = detect_intent(message.text)
    
    # Execute appropriate action
    action_handlers = {
        "generate_workout": lambda: execute_generate_workout(student_id, message.text),
        "check_fatigue": lambda: execute_check_fatigue(student_id, message.text),
        "explain_plan": lambda: execute_explain_plan(student_id, message.text, message.context),
        "record_feedback": lambda: execute_record_feedback(student_id, message.text, message.context),
        "exercise_recommendation": lambda: execute_exercise_recommendation(student_id, message.text),
        "progress_check": lambda: execute_progress_check(student_id, message.text),
        "general_chat": lambda: execute_general_chat(student_id, message.text),
    }
    
    handler = action_handlers.get(intent, action_handlers["general_chat"])
    response_data = handler()
    
    return ChatResponse(
        intent=intent,
        confidence=confidence,
        message=response_data["message"],
        action=response_data["action"],
        data=response_data["data"],
        llm_used=response_data.get("llm_used", False)
    )


@router.get("/intents")
def list_intents():
    """List all supported intents and their keywords."""
    return {
        "intents": [
            {
                "name": intent_name,
                "description": intent_data["description"],
                "sample_keywords": intent_data["keywords"][:5],
                "priority": INTENT_PRIORITY.index(intent_name) + 1
            }
            for intent_name, intent_data in INTENTS.items()
        ]
    }


@router.get("/test/{student_id}")
def test_chatbot(student_id: int):
    """Test endpoint to verify database connectivity and chatbot functionality."""
    try:
        # Test database queries
        profile = get_student_profile(student_id)
        fatigue = get_muscle_fatigue(student_id)
        plan = get_latest_plan(student_id)
        stats = get_progress_stats(student_id)
        
        return {
            "status": "healthy",
            "database_connected": True,
            "student_found": profile is not None,
            "has_fatigue_data": fatigue.get("status") != "No active fatigue data",
            "has_plans": plan is not None,
            "stats_available": stats["total_interactions"] > 0,
            "quick_test": {
                "profile_keys": list(profile.keys()) if profile else None,
                "fatigue_muscles": len(fatigue.get("muscles", {})),
                "latest_plan": plan["plan_id"] if plan else None,
                "completion_rate": stats["completion_rate"]
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
