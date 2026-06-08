"""
retrain.py
Automatic model retraining mechanism.
"""
import argparse
import json
import os
import shutil
from datetime import datetime, date
import joblib
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score
from feature_extractor import get_connection
from label_generator import generate_dataset

MODEL_PATH = "fitness_ranker.pkl"
MODEL_JSON_PATH = "fitness_ranker.json"
BACKUP_DIR = "model_backups"
LOG_PATH = "retrain_log.json"
TRAINING_DATA_PATH = "training_data.csv"

MIN_NEW_INTERACTIONS = 200
MIN_AUC_IMPROVEMENT = -0.01

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

def load_log() -> list:
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH) as f:
            return json.load(f)
    return []

def save_log(log: list):
    with open(LOG_PATH, "w") as f:
        json.dump(log, f, indent=2, default=str)

def last_retrain_date(log: list) -> date | None:
    completed = [e for e in log if e.get("status") == "replaced"]
    if not completed:
        return None
    return datetime.fromisoformat(completed[-1]["timestamp"]).date()

def count_new_interactions(since_date: date | None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    if since_date:
        cur.execute("""
            SELECT COUNT(*) FROM student_assigned_exercise_interaction
            WHERE interaction_date > %s
            AND exercise_status = 'COMPLETED'
        """, (since_date,))
    else:
        cur.execute("""
            SELECT COUNT(*) FROM student_assigned_exercise_interaction
            WHERE exercise_status = 'COMPLETED'
        """)
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count

def count_real_labels_available() -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(DISTINCT (saei.student_id, ae.exercise_id)) AS pairs,
            SUM(CASE WHEN saei.completed = TRUE THEN 1 ELSE 0 END)  AS completed,
            SUM(CASE WHEN saei.completed = FALSE THEN 1 ELSE 0 END) AS skipped
        FROM student_assigned_exercise_interaction saei
        JOIN assigned_exercise ae ON ae.assigned_exercise_id = saei.assigned_exercise_id
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    return {"pairs": row[0] or 0, "completed": row[1] or 0, "skipped": row[2] or 0}

def train_candidate(df: pd.DataFrame) -> tuple:
    X = df[FEATURE_COLS]
    y = df["label"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    pos_weight = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=pos_weight,
        eval_metric="auc",
        random_state=42,
        early_stopping_rounds=20,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
    auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    return model, round(auc, 4)

def evaluate_current_model(df: pd.DataFrame) -> float:
    if not os.path.exists(MODEL_PATH):
        return 0.0
    model = joblib.load(MODEL_PATH)
    X = df[FEATURE_COLS]
    y = df["label"]
    _, X_test, _, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    try:
        auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
        return round(auc, 4)
    except Exception:
        return 0.0

def backup_current_model():
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if os.path.exists(MODEL_PATH):
        shutil.copy(MODEL_PATH, f"{BACKUP_DIR}/fitness_ranker_{ts}.pkl")
    if os.path.exists(MODEL_JSON_PATH):
        shutil.copy(MODEL_JSON_PATH, f"{BACKUP_DIR}/fitness_ranker_{ts}.json")
    print(f"  📦 Backup saved → {BACKUP_DIR}/fitness_ranker_{ts}.pkl")

def check_readiness() -> dict:
    log = load_log()
    last_date = last_retrain_date(log)
    new_count = count_new_interactions(last_date)
    label_stats = count_real_labels_available()
    ready = new_count >= MIN_NEW_INTERACTIONS
    report = {
        "ready": ready,
        "new_interactions": new_count,
        "threshold": MIN_NEW_INTERACTIONS,
        "last_retrain_date": str(last_date) if last_date else "never",
        "total_pairs": label_stats["pairs"],
        "completed": label_stats["completed"],
        "skipped": label_stats["skipped"],
    }
    print(f"\n Retrain readiness report:")
    print(f"  Last retrain         : {report['last_retrain_date']}")
    print(f"  New interactions     : {new_count} / {MIN_NEW_INTERACTIONS} required")
    print(f"  Total labeled pairs  : {label_stats['pairs']}")
    print(f"  Ready to retrain     : {'✅ YES' if ready else '❌ NO'}")
    return report

def run_retrain(force: bool = False) -> dict:
    log = load_log()
    report = check_readiness()
    if not force and not report["ready"]:
        print(f"\n️  Skipping retrain — not enough new data ({report['new_interactions']} < {MIN_NEW_INTERACTIONS})")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "status": "skipped",
            "reason": f"only {report['new_interactions']} new interactions",
        }
        log.append(entry)
        save_log(log)
        return entry

    print(f"\n🔄 Starting retrain {'(forced)' if force else ''}...")
    print("  📊 Generating training dataset...")
    df = generate_dataset(n_students=500, exercises_per_student=15)
    df.to_csv(TRAINING_DATA_PATH, index=False)
    print(f"  Dataset: {len(df)} rows | positive rate: {df['label'].mean():.2%}")

    old_auc = evaluate_current_model(df)
    print(f"  Current model AUC : {old_auc:.4f}")

    print("  🚀 Training candidate model...")
    new_model, new_auc = train_candidate(df)
    print(f"  Candidate AUC     : {new_auc:.4f}")
    print(f"  Improvement       : {new_auc - old_auc:+.4f}")

    if new_auc >= old_auc + MIN_AUC_IMPROVEMENT:
        backup_current_model()
        joblib.dump(new_model, MODEL_PATH)
        new_model.save_model(MODEL_JSON_PATH)
        status = "replaced"
        print(f"  ✅ Model replaced (AUC {old_auc:.4f} → {new_auc:.4f})")
    else:
        status = "rejected"
        print(f"  ❌ Candidate rejected — AUC degraded too much ({old_auc:.4f} → {new_auc:.4f})")

    entry = {
        "timestamp": datetime.now().isoformat(),
        "status": status,
        "old_auc": old_auc,
        "new_auc": new_auc,
        "delta_auc": round(new_auc - old_auc, 4),
        "training_rows": len(df),
        "positive_rate": round(float(df["label"].mean()), 4),
        "new_interactions": report["new_interactions"],
        "forced": force,
    }
    log.append(entry)
    save_log(log)
    print(f"  📝 Logged → {LOG_PATH}")
    return entry

def retrain_history() -> list:
    log = load_log()
    print(f"\n Retrain history ({len(log)} entries):")
    for e in log:
        status_icon = {"replaced": "✅", "rejected": "", "skipped": "️"}.get(e["status"], "?")
        auc_info = f"AUC {e.get('old_auc','?'):.4f}→{e.get('new_auc','?'):.4f}" if "new_auc" in e else ""
        print(f"  {status_icon} {e['timestamp'][:16]}  {e['status']: <10}  {auc_info}")
    return log

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Model retraining manager")
    parser.add_argument("--force", action="store_true", help="Retrain regardless of threshold")
    parser.add_argument("--check-only", action="store_true", help="Only check readiness, don't train")
    parser.add_argument("--history", action="store_true", help="Show retrain history")
    args = parser.parse_args()
    if args.history:
        retrain_history()
    elif args.check_only:
        check_readiness()
    else:
        run_retrain(force=args.force)