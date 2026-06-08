"""
feature_extractor.py
Turns a (student_id, exercise_id) pair into a flat feature vector for XGBoost.
"""
import psycopg2
from datetime import date

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "fitness_db",
    "user": "postgres",
    "password": "1234",
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def extract_features(student_id: int, exercise_id: int, conn=None) -> dict:
    close_after = conn is None
    if conn is None:
        conn = get_connection()
    cur = conn.cursor()

    # ─ Student profile ──────────────────────────────────────────────────
    cur.execute("""
        SELECT s.age, s.gender,
               hp.medical_group_id, hp.height_cm, hp.weight_kg,
               hp.cooper_meters, hp.push_ups, hp.pull_ups,
               hp.flexibility_cm, hp.sit_ups, hp.jump_forward,
               a.bmi, a.strength_score, a.endurance_score, a.flexibility_score
        FROM students s
        JOIN students_health_profiles hp ON hp.student_id = s.student_id
        JOIN students_physical_readiness_assessments a ON a.health_profile_id = hp.health_profile_id
        WHERE s.student_id = %s
        LIMIT 1
    """, (student_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError(f"Student {student_id} not found")

    (age, gender, mg_id, height, weight,
     cooper, push_ups, pull_ups, flex, sit_ups, jump,
     bmi, strength_score, endurance_score, flex_score) = row

    gender_num = 1 if gender == "Male" else 0
    fitness_level = (float(strength_score) + float(endurance_score) + float(flex_score)) / 3

    # ── Exercise profile ──────────────────────────────────────────────────
    cur.execute("""
        SELECT difficulty, category_id,
               recommended_sets, recommended_reps, rest_between_sets_sec
        FROM exercises WHERE exercise_id = %s
    """, (exercise_id,))
    ex_row = cur.fetchone()
    if not ex_row:
        raise ValueError(f"Exercise {exercise_id} not found")

    difficulty, category_id, rec_sets, rec_reps, rest_sec = ex_row

    # ── Difficulty fit ────────────────────────────────────────────────────
    expected_difficulty = fitness_level * (5 / 4)
    difficulty_gap = abs(expected_difficulty - difficulty)
    difficulty_fit = max(0, 1 - difficulty_gap / 5)

    # ── Medical group safety ──────────────────────────────────────────────
    max_allowed = {1: 5, 2: 3, 3: 2}[mg_id]
    medical_ok = 1 if difficulty <= max_allowed else 0

    # ── Injury contraindication check ────────────────────────────────────
    cur.execute("""
        SELECT COUNT(*) FROM student_injury_history sih
        JOIN jt_exercise_contraindications jec ON jec.injury_type_id = sih.injury_type_id
        WHERE sih.student_id = %s
          AND jec.exercise_id = %s
          AND sih.recovery_status = 'active'
    """, (student_id, exercise_id))
    contraindicated = cur.fetchone()[0]
    injury_safe = 1 if contraindicated == 0 else 0

    # ── Muscle freshness from muscle_fatigue table ────────────────────────
    cur.execute("""
        SELECT muscle_group_id FROM jt_exercise_muscle_group
        WHERE exercise_id = %s
    """, (exercise_id,))
    muscle_group_ids = [r[0] for r in cur.fetchall()]

    if muscle_group_ids:
        cur.execute("""
            SELECT mf.assigned_exercise_muscle_group_id,
                   aemg.muscle_group_id,
                   mf.recovery_left,
                   mf.status
            FROM muscle_fatigue mf
            JOIN assigned_exercise_muscle_group aemg
                ON aemg.assigned_exercise_muscle_group_id = mf.assigned_exercise_muscle_group_id
            WHERE mf.student_id = %s
               AND aemg.muscle_group_id = ANY(%s)
              AND mf.status = 'ACTIVE'
            ORDER BY mf.date DESC
        """, (student_id, muscle_group_ids))
        fatigue_rows = cur.fetchall()
        if fatigue_rows:
            max_recovery_left = max(r[2] for r in fatigue_rows)
            fatigue_ratio = min(1.0, max_recovery_left / 72.0)
            muscle_freshness = round(1.0 - fatigue_ratio, 3)
        else:
            muscle_freshness = 1.0
    else:
        muscle_freshness = 1.0

    # ── Completion rate from real interaction history ──────────────────────
    cur.execute("""
        SELECT
            COUNT(*)                                            AS total,
            SUM(CASE WHEN completed = TRUE THEN 1 ELSE 0 END)  AS done,
            AVG(CASE
                 WHEN perceived_difficulty = 'Very Easy' THEN 1
                WHEN perceived_difficulty = 'Easy'      THEN 2
                WHEN perceived_difficulty = 'Normal'    THEN 3
                WHEN perceived_difficulty = 'Hard'      THEN 4
                WHEN perceived_difficulty = 'Very Hard' THEN 5
                ELSE NULL END)                                  AS avg_difficulty_perception,
            AVG(CASE WHEN ae.recommended_sets > 0
                THEN saei.actually_sets::float / NULLIF(ae.recommended_sets, 0)
                ELSE NULL END)                                  AS avg_set_completion_ratio
        FROM student_assigned_exercise_interaction saei
        JOIN assigned_exercise ae ON ae.assigned_exercise_id = saei.assigned_exercise_id
        WHERE saei.student_id = %s
          AND ae.exercise_id  = %s
    """, (student_id, exercise_id))
    hist = cur.fetchone()
    total_attempts, done, avg_perc_diff, avg_set_ratio = hist

    if total_attempts and total_attempts > 0:
        historical_completion_rate = round(float(done) / float(total_attempts), 3)
        avg_perceived_difficulty = round(float(avg_perc_diff), 3) if avg_perc_diff else 3.0
        avg_set_completion_ratio = round(float(avg_set_ratio), 3) if avg_set_ratio else 1.0
    else:
        historical_completion_rate = 0.5
        avg_perceived_difficulty = 3.0
        avg_set_completion_ratio = 1.0

    # ── Plan-level satisfaction signal ────────────────────────────────────
    cur.execute("""
        SELECT
            COUNT(*)                                                AS total_plans,
            SUM(CASE WHEN wp.satisfaction = 'Liked' THEN 1 ELSE 0 END) AS liked
        FROM student_assigned_exercise_interaction saei
        JOIN assigned_exercise ae  ON ae.assigned_exercise_id = saei.assigned_exercise_id
        JOIN workout_plan wp       ON wp.workout_plan_id  = saei.workout_plan_id
        WHERE saei.student_id = %s
          AND ae.exercise_id  = %s
          AND wp.satisfaction IS NOT NULL
    """, (student_id, exercise_id))
    sat = cur.fetchone()
    total_plans, liked_plans = sat
    plan_satisfaction_rate = round(float(liked_plans) / float(total_plans), 3) if total_plans and total_plans > 0 else 0.5

    # ─ Category flags ────────────────────────────────────────────────────
    is_warmup = 1 if category_id == 1 else 0
    is_cardio = 1 if category_id == 2 else 0
    is_strength = 1 if category_id == 3 else 0
    is_stretching = 1 if category_id == 4 else 0
    is_core = 1 if category_id == 5 else 0

    features = {
        "age": age,
        "gender": gender_num,
        "medical_group_id": mg_id,
        "bmi": float(bmi),
        "strength_score": float(strength_score),
        "endurance_score": float(endurance_score),
        "flex_score": float(flex_score),
        "fitness_level": round(fitness_level, 3),
        "cooper_meters": cooper,
        "push_ups": push_ups,
        "pull_ups": pull_ups,
        "difficulty": difficulty,
        "category_id": category_id,
        "rec_sets": rec_sets,
        "rec_reps": rec_reps,
        "rest_sec": rest_sec,
        "difficulty_gap": round(difficulty_gap, 3),
        "difficulty_fit": round(difficulty_fit, 3),
        "medical_ok": medical_ok,
        "injury_safe": injury_safe,
        "muscle_freshness": muscle_freshness,
        "historical_completion_rate": historical_completion_rate,
        "avg_perceived_difficulty": avg_perceived_difficulty,
        "avg_set_completion_ratio": avg_set_completion_ratio,
        "plan_satisfaction_rate": plan_satisfaction_rate,
        "is_warmup": is_warmup,
        "is_cardio": is_cardio,
        "is_strength": is_strength,
        "is_stretching": is_stretching,
        "is_core": is_core,
    }

    cur.close()
    if close_after:
        conn.close()
    return features

if __name__ == "__main__":
    feats = extract_features(student_id=1, exercise_id=11)
    for k, v in feats.items():
        print(f"  {k:35s}: {v}")