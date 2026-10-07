"""Build recommendation features with a fixed number of database queries."""
import psycopg2
from core.settings import settings


def _sync_db_url() -> str:
    # psycopg2 accepts a PostgreSQL URI, not SQLAlchemy driver suffixes.
    return settings.DB_URL.replace('postgresql+asyncpg://', 'postgresql://').replace('postgresql+psycopg2://', 'postgresql://')


def get_connection():
    return psycopg2.connect(_sync_db_url(), connect_timeout=10)


def extract_features_batch(student_id: int, exercise_ids: list[int], conn=None) -> dict[int, dict]:
    """Fetch student context once and aggregate history for all candidate exercises.

    Uses six queries regardless of the candidate count. Results preserve the
    feature definitions used by the existing trained model.
    """
    ids = list(dict.fromkeys(exercise_ids))
    if not ids:
        return {}
    own_connection = conn is None
    conn = conn or get_connection()
    cur = conn.cursor()
    try:
        cur.execute('''
            SELECT s.age, s.gender, hp.medical_group_id, hp.cooper_meters,
                   hp.push_ups, hp.pull_ups, a."BMI", a.strength_score,
                   a.endurance_score, a.flexibility_score
            FROM students s
            JOIN students_health_profiles hp ON hp.student_id = s.student_id
            JOIN students_physical_readiness_assessments a ON a.health_profile_id = hp.health_profile_id
            WHERE s.student_id = %s LIMIT 1
        ''', (student_id,))
        profile = cur.fetchone()
        if not profile:
            raise ValueError(f'Student {student_id} has no physical assessment')
        age, gender, medical_group, cooper, pushups, pullups, bmi, strength, endurance, flexibility = profile
        fitness = (float(strength) + float(endurance) + float(flexibility)) / 3

        cur.execute('''SELECT exercise_id, difficulty, category_id, recommended_sets,
                              recommended_reps, rest_between_sets_sec
                       FROM exercises WHERE exercise_id = ANY(%s)''', (ids,))
        exercises = cur.fetchall()
        cur.execute('''SELECT DISTINCT ec.exercise_id
                       FROM student_injury_history sih
                       JOIN exercise_contraindications ec ON ec.injury_type_id = sih.injury_type_id
                       WHERE sih.student_id = %s AND sih.recovery_status = 'active'
                         AND ec.exercise_id = ANY(%s)''', (student_id, ids))
        contraindicated = {row[0] for row in cur.fetchall()}
        cur.execute('''SELECT emg.exercise_id, MAX(mf.recovery_left)
                       FROM exercise_muscle_group emg
                       JOIN assigned_exercise_muscle_group aemg ON aemg.muscle_group_id = emg.muscle_group_id
                       JOIN muscle_fatigue mf ON mf.assigned_exercise_muscle_group_id = aemg.assigned_exercise_muscle_group_id
                       WHERE mf.student_id = %s AND mf.status = 'ACTIVE'
                         AND emg.exercise_id = ANY(%s)
                       GROUP BY emg.exercise_id''', (student_id, ids))
        recovery = dict(cur.fetchall())
        cur.execute('''
            SELECT ae.exercise_id, COUNT(*),
                   SUM(CASE WHEN saei.completed = TRUE THEN 1 ELSE 0 END),
                   AVG(CASE saei.perceived_difficulty
                       WHEN 'Very Easy' THEN 1 WHEN 'Easy' THEN 2 WHEN 'Normal' THEN 3
                       WHEN 'Hard' THEN 4 WHEN 'Very Hard' THEN 5 ELSE NULL END),
                   AVG(CASE WHEN ae.recommended_sets > 0
                       THEN saei.actually_sets::float / NULLIF(ae.recommended_sets, 0) ELSE NULL END)
            FROM student_assigned_exercise_interaction saei
            JOIN assigned_exercise ae ON ae.assigned_exercise_id = saei.assigned_exercise_id
            WHERE saei.student_id = %s AND ae.exercise_id = ANY(%s)
            GROUP BY ae.exercise_id
        ''', (student_id, ids))
        history = {row[0]: row[1:] for row in cur.fetchall()}
        cur.execute('''
            SELECT ae.exercise_id, COUNT(*), SUM(CASE WHEN wp.satisfaction = 'Liked' THEN 1 ELSE 0 END)
            FROM student_assigned_exercise_interaction saei
            JOIN assigned_exercise ae ON ae.assigned_exercise_id = saei.assigned_exercise_id
            JOIN workout_plan wp ON wp.workout_plan_id = saei.workout_plan_id
            WHERE saei.student_id = %s AND ae.exercise_id = ANY(%s) AND wp.satisfaction IS NOT NULL
            GROUP BY ae.exercise_id
        ''', (student_id, ids))
        satisfaction = {row[0]: row[1:] for row in cur.fetchall()}
        results = {}
        for exercise_id, raw_difficulty, category, sets, reps, rest in exercises:
            difficulty = {'low': 1, 'medium': 3, 'high': 5}.get(str(raw_difficulty).lower(), 3)
            gap = abs(fitness * (5 / 4) - difficulty)
            total, done, perceived, ratio = history.get(exercise_id, (0, 0, None, None))
            plan_total, liked = satisfaction.get(exercise_id, (0, 0))
            results[exercise_id] = {
                'age': age, 'gender': 1 if gender == 'Male' else 0,
                'medical_group_id': medical_group, 'bmi': float(bmi),
                'strength_score': float(strength), 'endurance_score': float(endurance),
                'flex_score': float(flexibility), 'fitness_level': round(fitness, 3),
                'cooper_meters': cooper, 'push_ups': pushups, 'pull_ups': pullups,
                'difficulty': difficulty, 'category_id': category, 'rec_sets': sets,
                'rec_reps': reps, 'rest_sec': rest, 'difficulty_gap': round(gap, 3),
                'difficulty_fit': round(max(0, 1 - gap / 5), 3),
                'medical_ok': int(difficulty <= {1: 5, 2: 3, 3: 2}[medical_group]),
                'injury_safe': int(exercise_id not in contraindicated),
                'muscle_freshness': round(1 - min(1.0, recovery.get(exercise_id, 0) / 72.0), 3),
                'historical_completion_rate': round(float(done) / total, 3) if total else 0.5,
                'avg_perceived_difficulty': round(float(perceived), 3) if perceived else 3.0,
                'avg_set_completion_ratio': round(float(ratio), 3) if ratio else 1.0,
                'plan_satisfaction_rate': round(float(liked) / plan_total, 3) if plan_total else 0.5,
                'is_warmup': int(category == 1), 'is_cardio': int(category == 2),
                'is_strength': int(category == 3), 'is_stretching': int(category == 4),
                'is_core': int(category == 5),
            }
        return results
    finally:
        cur.close()
        if own_connection:
            conn.close()


def extract_features(student_id: int, exercise_id: int, conn=None) -> dict:
    features = extract_features_batch(student_id, [exercise_id], conn)
    if exercise_id not in features:
        raise ValueError(f'Exercise {exercise_id} not found')
    return features[exercise_id]