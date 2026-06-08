"""
label_generator.py
Generates (student, exercise, label) training pairs.
"""
import psycopg2
import pandas as pd
import random
from feature_extractor import extract_features, get_connection

random.seed(42)

def real_label_from_history(student_id: int, exercise_id: int, conn) -> int | None:
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(*)                                                       AS total,
            AVG(CASE WHEN saei.completed = TRUE THEN 1.0 ELSE 0.0 END)    AS completion_rate,
            AVG(CASE
                WHEN saei.perceived_difficulty = 'Very Easy' THEN 1
                WHEN saei.perceived_difficulty = 'Easy'      THEN 2
                WHEN saei.perceived_difficulty = 'Normal'    THEN 3
                WHEN saei.perceived_difficulty = 'Hard'      THEN 4
                WHEN saei.perceived_difficulty = 'Very Hard' THEN 5
                ELSE NULL END)                                             AS avg_perc_diff,
            AVG(CASE
                WHEN ae.recommended_sets > 0 AND saei.completed = TRUE
                THEN saei.actually_sets::float / NULLIF(ae.recommended_sets, 0)
                ELSE NULL END)                                             AS avg_set_ratio
        FROM student_assigned_exercise_interaction saei
        JOIN assigned_exercise ae ON ae.assigned_exercise_id = saei.assigned_exercise_id
        WHERE saei.student_id = %s
          AND ae.exercise_id  = %s
    """, (student_id, exercise_id))
    row = cur.fetchone()
    cur.close()

    total, completion_rate, avg_perc_diff, avg_set_ratio = row
    if not total or total == 0:
        return None

    completion_rate = float(completion_rate)
    avg_perc_diff = float(avg_perc_diff) if avg_perc_diff else 3.0
    avg_set_ratio = float(avg_set_ratio) if avg_set_ratio else 1.0

    if completion_rate >= 0.6 and avg_perc_diff <= 3.5 and avg_set_ratio >= 0.7:
        return 1
    if completion_rate < 0.4 or avg_perc_diff > 4.0 or avg_set_ratio < 0.5:
        return 0
    return None

def synthetic_label(features: dict) -> int:
    if features["injury_safe"] == 0:
        return 0
    if features["medical_ok"] == 0:
        return 0
    if features["difficulty_gap"] > 2.5:
        return 0
    if features["muscle_freshness"] < 0.28 and features["is_strength"] == 1:
        return 0

    score = 0
    if features["difficulty_fit"] > 0.7:
        score += 2
    elif features["difficulty_fit"] > 0.4:
        score += 1
    if features["muscle_freshness"] > 0.6:
        score += 1
    if features["fitness_level"] >= 3.0 and (features["is_strength"] or features["is_cardio"]):
        score += 1
    if features["fitness_level"] < 2.0 and (features["is_warmup"] or features["is_stretching"] or features["is_core"]):
        score += 1
    if features["medical_group_id"] == 3 and features["difficulty"] <= 2:
        score += 1
    if features["historical_completion_rate"] >= 0.7:
        score += 1
    if features["avg_perceived_difficulty"] <= 2.5:
        score += 1
    if features["avg_set_completion_ratio"] >= 0.8:
        score += 1

    return 1 if score >= 2 else 0

def generate_dataset(n_students: int = 500, exercises_per_student: int = 15) -> pd.DataFrame:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT exercise_id FROM exercises ORDER BY exercise_id")
    all_exercise_ids = [row[0] for row in cur.fetchall()]
    cur.close()

    records = []
    real_count = 0
    synthetic_count = 0

    for student_id in range(1, n_students + 1):
        sampled = random.sample(all_exercise_ids, min(exercises_per_student, len(all_exercise_ids)))
        for exercise_id in sampled:
            try:
                feats = extract_features(student_id, exercise_id, conn=conn)
                label = real_label_from_history(student_id, exercise_id, conn)
                if label is not None:
                    real_count += 1
                else:
                    label = synthetic_label(feats)
                    synthetic_count += 1
                feats["student_id"] = student_id
                feats["exercise_id"] = exercise_id
                feats["label"] = label
                records.append(feats)
            except Exception as e:
                print(f"  Skipping student={student_id} exercise={exercise_id}: {e}")
        if student_id % 50 == 0:
            print(f"  Processed {student_id}/{n_students} students (real={real_count}, synthetic={synthetic_count})...")

    conn.close()
    df = pd.DataFrame(records)
    print(f"\n✅ Dataset: {len(df)} rows")
    print(f"   Real labels      : {real_count}  ({real_count/len(df)*100:.1f}%)")
    print(f"   Synthetic labels : {synthetic_count}  ({synthetic_count/len(df)*100:.1f}%)")
    print(f"   Positive rate    : {df['label'].mean():.2%}")
    return df

if __name__ == "__main__":
    df = generate_dataset(n_students=500, exercises_per_student=15)
    df.to_csv("training_data.csv", index=False)
    print("💾 Saved → training_data.csv")