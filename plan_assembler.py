"""
plan_assembler.py
Builds a personalized weekly workout plan for a student and saves it to DB.
"""
import argparse
import joblib
import pandas as pd
from datetime import date, timedelta
from feature_extractor import extract_features, get_connection

CONSTRUCTION_STANDARD = {"warmup": 2, "main": 3, "cooldown": 2}
WEEKLY_TEMPLATE = [
    {"day": "MONDAY",    "focus": "strength", "main_categories": [3]},
    {"day": "WEDNESDAY", "focus": "strength", "main_categories": [3]},
    {"day": "FRIDAY",    "focus": "cardio",   "main_categories": [2, 5]},
]
WARMUP_CATEGORIES = [1]
COOLDOWN_CATEGORIES = [4, 5]

EXERCISE_MUSCLES = {
    1:[7,9],2:[3],3:[7,9],4:[7,6],5:[9],6:[7,8],7:[6,7],8:[7,10],9:[6,7],10:[7,9],
    11:[1,5],12:[2,4],13:[7,9],14:[2,8,9],15:[1,5],16:[3,5],17:[2,3],18:[7,9],19:[4],20:[5],
    21:[7],22:[8],23:[1,3],24:[2,6],25:[2],26:[6],27:[6],28:[6],29:[6],30:[6],
}

FEATURE_COLS = [
    "age", "gender", "medical_group_id", "bmi",
    "strength_score", "endurance_score", "flex_score", "fitness_level",
    "cooper_meters", "push_ups", "pull_ups",
    "difficulty", "category_id", "rec_sets", "rec_reps", "rest_sec",
    "difficulty_gap", "difficulty_fit", "medical_ok", "injury_safe",
    "muscle_freshness",
    "historical_completion_rate", "avg_perceived_difficulty",
    "avg_set_completion_ratio", "plan_satisfaction_rate",
    "is_warmup", "is_cardio", "is_strength", "is_stretching", "is_core",
]

def load_all_exercises(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT e.exercise_id, e.exercise_name, e.category_id, e.difficulty,
               e.recommended_sets, e.recommended_reps, e.rest_between_sets_sec,
               ec.category_name
        FROM exercises e
        JOIN exercise_categories ec ON ec.category_id = e.category_id
        ORDER BY e.exercise_id
    """)
    cols = ["exercise_id","exercise_name","category_id","difficulty",
            "recommended_sets","recommended_reps","rest_sec","category_name"]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close()
    return rows

def filter_exercises(student_id, exercises, conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT medical_group_id FROM students_health_profiles
        WHERE student_id = %s LIMIT 1
    """, (student_id,))
    row = cur.fetchone()
    mg_id = row[0] if row else 1
    max_difficulty = {1: 5, 2: 3, 3: 2}[mg_id]

    cur.execute("""
        SELECT DISTINCT jec.exercise_id
        FROM student_injury_history sih
        JOIN exercise_contraindications jec ON jec.injury_type_id = sih.injury_type_id
        WHERE sih.student_id = %s AND sih.recovery_status = 'active'
    """, (student_id,))
    contraindicated = {r[0] for r in cur.fetchall()}
    cur.close()

    DIFFICULTY_MAP = {'low': 1, 'medium': 3, 'high': 5}
    return [
        ex for ex in exercises
        if ex["exercise_id"] not in contraindicated
        and DIFFICULTY_MAP.get(str(ex["difficulty"]).lower(), 3) <= max_difficulty
    ]

def rank_exercises(student_id, exercises, model, conn):
    scored = []
    for ex in exercises:
        try:
            feats = extract_features(student_id, ex["exercise_id"], conn=conn)
            vec = pd.DataFrame([{c: feats[c] for c in FEATURE_COLS}])
            score = model.predict_proba(vec)[0][1]
            # ✅ FIX: Cast numpy.float to native Python float so psycopg2 can read it
            scored.append({**ex, "score": round(float(score), 4)})
        except Exception as e:
            print(f"  Warning: could not score exercise {ex['exercise_id']}: {e}")
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored

def pick_slot(ranked, categories, n, used_ids):
    picked = []
    for ex in ranked:
        if len(picked) == n:
            break
        if ex["exercise_id"] not in used_ids and ex["category_id"] in categories:
            picked.append(ex)
    return picked

def assemble_plan(ranked):
    used_ids = set()
    weekly = []
    for day_config in WEEKLY_TEMPLATE:
        warmup = pick_slot(ranked, WARMUP_CATEGORIES, CONSTRUCTION_STANDARD["warmup"], used_ids)
        main = pick_slot(ranked, day_config["main_categories"], CONSTRUCTION_STANDARD["main"], used_ids)
        cooldown = pick_slot(ranked, COOLDOWN_CATEGORIES, CONSTRUCTION_STANDARD["cooldown"], used_ids)
        for ex in warmup + main + cooldown:
            used_ids.add(ex["exercise_id"])
        weekly.append({
            "day": day_config["day"],
            "focus": day_config["focus"],
            "warmup": warmup,
            "main": main,
            "cooldown": cooldown,
        })
    return weekly

def save_plan_to_db(student_id, weekly_plan, conn):
    cur = conn.cursor()
    today = date.today()
    plan_ids = []
    day_offsets = {"MONDAY": 0, "WEDNESDAY": 2, "FRIDAY": 4}
    for session in weekly_plan:
        plan_date = today + timedelta(days=day_offsets[session["day"]])
        cur.execute("""
            INSERT INTO workout_plan
                (student_id, workout_standard_id, date, workout_status)
            VALUES (%s, 1, %s, 'SCHEDULED')
            RETURNING workout_plan_id
        """, (student_id, plan_date))
        plan_id = cur.fetchone()[0]
        plan_ids.append(plan_id)
        order = 1
        for slot_type in ["warmup", "main", "cooldown"]:
            for ex in session[slot_type]:
                cur.execute("""
                    INSERT INTO assigned_exercise
                        (workout_plan_id, exercise_id, slot_type, day_of_week,
                         order_in_session, predicted_score,
                         recommended_sets, recommended_reps)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING assigned_exercise_id
                """, (plan_id, ex["exercise_id"], slot_type, session["day"],
                      order, ex["score"],
                      ex["recommended_sets"], ex["recommended_reps"]))
                ae_id = cur.fetchone()[0]
                for mg_id in EXERCISE_MUSCLES.get(ex["exercise_id"], []):
                    cur.execute("""
                        INSERT INTO assigned_exercise_muscle_group
                            (assigned_exercise_id, muscle_group_id)
                        VALUES (%s, %s)
                    """, (ae_id, mg_id))
                order += 1
    conn.commit()
    cur.close()
    return plan_ids

def format_plan(student_id, weekly_plan, conn):
    cur = conn.cursor()
    cur.execute("SELECT student_name FROM students WHERE student_id = %s", (student_id,))
    name = cur.fetchone()[0]
    cur.close()
    lines = [
        f"\n{'═'*60}",
        f"  Weekly Workout Plan — {name} (student #{student_id})",
        f"{'═'*60}",
    ]
    for session in weekly_plan:
        lines.append(f"\n  {session['day']}  [{session['focus']} focus]")
        lines.append(f"  {'─'*52}")
        for slot_name in ["warmup", "main", "cooldown"]:
            lines.append(f"  {slot_name.capitalize()}:")
            for ex in session[slot_name]:
                lines.append(
                    f"    • {ex['exercise_name']: <28}  "
                    f"{ex['recommended_sets']}×{ex['recommended_reps']}   "
                    f"rest {ex['rest_sec']}s   "
                    f"[score {ex['score']}]"
                )
            if not session[slot_name]:
                lines.append("    (no exercises available)")
    lines.append(f"\n{'═'*60}\n")
    return "\n".join(lines)

def generate_plan(student_id: int, model_path: str = "fitness_ranker.pkl",
                  save_to_db: bool = True) -> dict:
    print(f"🔄 Generating plan for student #{student_id}...")
    model = joblib.load(model_path)
    conn = get_connection()
    exercises = load_all_exercises(conn)
    print(f"  Total exercises       : {len(exercises)}")
    safe = filter_exercises(student_id, exercises, conn)
    print(f"  After safety filter   : {len(safe)} remain")
    ranked = rank_exercises(student_id, safe, model, conn)
    print(f"  Ranked by XGBoost     : {len(ranked)} scored")
    weekly_plan = assemble_plan(ranked)
    if save_to_db:
        plan_ids = save_plan_to_db(student_id, weekly_plan, conn)
        print(f"  Saved to DB           : workout_plan_ids {plan_ids}")
    print(format_plan(student_id, weekly_plan, conn))
    conn.close()
    return weekly_plan

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a weekly workout plan.")
    parser.add_argument("--student_id", type=int, default=1)
    parser.add_argument("--model", type=str, default="fitness_ranker.pkl")
    parser.add_argument("--no-save", action="store_true")
    args = parser.parse_args()
    generate_plan(args.student_id, args.model, save_to_db=not args.no_save)