"""
train_model.py
Trains XGBoost on the generated dataset.
"""
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt

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

print("📂 Loading training data...")
df = pd.read_csv("training_data.csv")
X = df[FEATURE_COLS]
y = df["label"]
print(f"  Total samples : {len(df)}")
print(f"  Positive rate : {y.mean():.2%}")
print(f"  Features      : {len(FEATURE_COLS)}")

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)
print(f"  Train: {len(X_train)} | Test: {len(X_test)}")

print("\n🚀 Training XGBoost...")
model = xgb.XGBClassifier(
    n_estimators=300,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    scale_pos_weight=(y_train == 0).sum() / max((y_train == 1).sum(), 1),
    eval_metric="auc",
    random_state=42,
    early_stopping_rounds=20,
)
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

y_pred = model.predict(X_test)
y_pred_prob = model.predict_proba(X_test)[:, 1]
auc = roc_auc_score(y_test, y_pred_prob)
print(f"\n📊 Results:")
print(f"  AUC-ROC : {auc:.4f}")
print(f"\n{classification_report(y_test, y_pred, target_names=['Bad fit', 'Good fit'])}")
print(f"  Confusion matrix:\n{confusion_matrix(y_test, y_pred)}")

importance = pd.Series(model.feature_importances_, index=FEATURE_COLS).sort_values(ascending=False)
print(f"\n🔑 Top 10 features:")
print(importance.head(10).to_string())
plt.figure(figsize=(10, 7))
importance.head(15).plot(kind="barh", color="steelblue")
plt.title("XGBoost Feature Importance (Top 15)")
plt.xlabel("Importance")
plt.tight_layout()
plt.savefig("feature_importance.png", dpi=120)
print("\n Saved → feature_importance.png")

joblib.dump(model, "fitness_ranker.pkl")
model.save_model("fitness_ranker.json")
print(" Saved → fitness_ranker.pkl + fitness_ranker.json")

print("\n🎯 Demo: ranking all exercises for student_id=1")
from feature_extractor import extract_features, get_connection
conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT exercise_id, exercise_name FROM exercises ORDER BY exercise_id")
all_exercises = cur.fetchall()
cur.close()
rows = []
for ex_id, ex_name in all_exercises:
    try:
        feats = extract_features(1, ex_id, conn=conn)
        vec = pd.DataFrame([{c: feats[c] for c in FEATURE_COLS}])
        score = model.predict_proba(vec)[0][1]
        rows.append({"exercise_id": ex_id, "name": ex_name, "score": round(score, 4)})
    except Exception as e:
        print(f"  Warning: {e}")
conn.close()
ranked = pd.DataFrame(rows).sort_values("score", ascending=False)
print(ranked.to_string(index=False))