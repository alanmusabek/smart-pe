"""
explainability.py
Two levels of explanation for the XGBoost recommendation model.
"""
import shap
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")
from feature_extractor import extract_features, get_connection

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

FEATURE_LABELS_RU = {
    "difficulty_fit": "Соответствие сложности уровню студента",
    "muscle_freshness": "Восстановление мышц",
    "injury_safe": "Безопасность при травмах",
    "medical_ok": "Соответствие медицинской группе",
    "historical_completion_rate": "Процент выполнения в прошлом",
    "avg_perceived_difficulty": "Субъективная сложность",
    "avg_set_completion_ratio": "Выполненный объём нагрузки",
    "plan_satisfaction_rate": "Удовлетворённость предыдущими планами",
    "fitness_level": "Общий уровень физподготовки",
    "difficulty_gap": "Разрыв между сложностью и уровнем",
    "endurance_score": "Оценка выносливости",
    "strength_score": "Оценка силы",
    "flex_score": "Оценка гибкости",
    "bmi": "Индекс массы тела",
    "is_warmup": "Категория: разминка",
    "is_cardio": "Категория: кардио",
    "is_strength": "Категория: силовые",
    "is_stretching": "Категория: растяжка",
    "is_core": "Категория: кор",
}

DIFFICULTY_LABELS = {
    1: "Очень лёгкое", 2: "Лёгкое", 3: "Среднее", 4: "Сложное", 5: "Очень сложное"
}
MEDICAL_GROUP_LABELS = {
    1: "Основная (без ограничений)",
    2: "Подготовительная (умеренная нагрузка)",
    3: "Специальная (щадящий режим)",
}

def load_explainer(model_path: str = "fitness_ranker.pkl") -> tuple:
    model = joblib.load(model_path)
    explainer = shap.TreeExplainer(model)
    return model, explainer

def explain_exercise(student_id: int, exercise_id: int,
                     model_path: str = "fitness_ranker.pkl",
                     plot: bool = False, plot_path: str = None) -> dict:
    model, explainer = load_explainer(model_path)
    conn = get_connection()
    feats = extract_features(student_id, exercise_id, conn=conn)
    conn.close()

    vec = pd.DataFrame([{c: feats[c] for c in FEATURE_COLS}])
    score = model.predict_proba(vec)[0][1]
    shap_vals = explainer.shap_values(vec)
    if isinstance(shap_vals, list):
        shap_vals = shap_vals[1]

    shap_dict = dict(zip(FEATURE_COLS, shap_vals[0]))
    sorted_shap = sorted(shap_dict.items(), key=lambda x: abs(x[1]), reverse=True)

    top_positive = [(f, v) for f, v in sorted_shap if v > 0][:3]
    top_negative = [(f, v) for f, v in sorted_shap if v < 0][:3]

    if plot:
        _plot_shap_waterfall(shap_vals[0], vec, plot_path or f"shap_s{student_id}_e{exercise_id}.png")

    return {
        "student_id": student_id,
        "exercise_id": exercise_id,
        "score": round(float(score), 4),
        "shap_values": {f: round(float(v), 4) for f, v in sorted_shap},
        "top_positive": [(f, round(float(v), 4)) for f, v in top_positive],
        "top_negative": [(f, round(float(v), 4)) for f, v in top_negative],
        "feature_values": {f: feats[f] for f in FEATURE_COLS},
    }

def explain_plan_shap(student_id: int, weekly_plan: list,
                      model_path: str = "fitness_ranker.pkl",
                      plot_path: str = "shap_plan_summary.png") -> pd.DataFrame:
    model, explainer = load_explainer(model_path)
    conn = get_connection()
    rows = []
    for session in weekly_plan:
        for slot in ["warmup", "main", "cooldown"]:
            for ex in session[slot]:
                feats = extract_features(student_id, ex["exercise_id"], conn=conn)
                vec = pd.DataFrame([{c: feats[c] for c in FEATURE_COLS}])
                shap_vals = explainer.shap_values(vec)
                if isinstance(shap_vals, list):
                    shap_vals = shap_vals[1]
                row = {"exercise_name": ex["exercise_name"], "slot": slot, "day": session["day"]}
                for feat, val in zip(FEATURE_COLS, shap_vals[0]):
                    row[feat] = round(float(val), 4)
                rows.append(row)
    conn.close()
    df = pd.DataFrame(rows)

    mean_abs_shap = df[FEATURE_COLS].abs().mean().sort_values(ascending=False).head(15)
    labels = [FEATURE_LABELS_RU.get(f, f) for f in mean_abs_shap.index]

    plt.figure(figsize=(10, 7))
    plt.barh(labels[::-1], mean_abs_shap.values[::-1], color="steelblue")
    plt.title(f"SHAP Feature Impact — Weekly Plan (Student #{student_id})")
    plt.xlabel("Mean |SHAP value|")
    plt.tight_layout()
    plt.savefig(plot_path, dpi=120)
    plt.close()
    print(f" SHAP summary saved → {plot_path}")
    return df

def _plot_shap_waterfall(shap_vals, vec, path):
    feat_vals = vec.iloc[0]
    shap_s = pd.Series(shap_vals, index=FEATURE_COLS).sort_values()
    labels = [FEATURE_LABELS_RU.get(f, f) for f in shap_s.index]
    colors = ["#e05c5c" if v < 0 else "#5c9ee0" for v in shap_s.values]
    plt.figure(figsize=(10, 8))
    plt.barh(labels, shap_s.values, color=colors)
    plt.axvline(0, color="black", linewidth=0.8)
    plt.title("SHAP Waterfall — Feature Contributions")
    plt.xlabel("SHAP value (impact on prediction)")
    plt.tight_layout()
    plt.savefig(path, dpi=120)
    plt.close()
    print(f"📊 SHAP waterfall saved → {path}")

def _fitness_label(score: float) -> str:
    if score >= 3.5: return "отличный"
    if score >= 2.5: return "хороший"
    if score >= 1.5: return "удовлетворительный"
    return "низкий"

def _freshness_label(f: float) -> str:
    if f >= 0.8: return "полностью восстановлены"
    if f >= 0.5: return "достаточно восстановлены"
    if f >= 0.2: return "ещё восстанавливаются"
    return "не восстановлены"

def explain_exercise_ru(student_id: int, exercise_id: int,
                        model_path: str = "fitness_ranker.pkl") -> str:
    result = explain_exercise(student_id, exercise_id, model_path)
    feats = result["feature_values"]
    score = result["score"]
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT student_name FROM students WHERE student_id = %s", (student_id,))
    student_name = cur.fetchone()[0]
    cur.execute("SELECT exercise_name, difficulty FROM exercises WHERE exercise_id = %s", (exercise_id,))
    ex_name, difficulty = cur.fetchone()
    cur.close()
    conn.close()

    lines = [f'Упражнение: "{ex_name}"']
    lines.append(f"Оценка модели: {score:.0%} — {'рекомендуется' if score >= 0.5 else 'не рекомендуется'}\n")
    fl = feats["fitness_level"]
    lines.append(f"• Уровень физподготовки студента: {_fitness_label(fl)} ({fl:.1f}/4.0)")
    diff_fit = feats["difficulty_fit"]
    ex_diff = DIFFICULTY_LABELS.get(difficulty, str(difficulty))
    if diff_fit >= 0.7:
        lines.append(f"• Сложность упражнения ({ex_diff}) хорошо соответствует уровню студента")
    elif diff_fit >= 0.4:
        lines.append(f"• Сложность ({ex_diff}) немного не совпадает с уровнем студента")
    else:
        lines.append(f"• ⚠️  Сложность ({ex_diff}) значительно отличается от уровня студента")
    mf = feats["muscle_freshness"]
    lines.append(f"• Задействованные мышцы {_freshness_label(mf)}")
    if feats["injury_safe"] == 1:
        lines.append("• Упражнение безопасно с учётом текущих травм студента")
    else:
        lines.append("• ⚠️  Упражнение противопоказано при текущих травмах")
    mg = int(feats["medical_group_id"])
    mok = feats["medical_ok"]
    lines.append(f"• Медицинская группа: {MEDICAL_GROUP_LABELS.get(mg, mg)}  "
                 f"{'✓' if mok else '⚠️  превышает допустимую нагрузку'}")
    hcr = feats["historical_completion_rate"]
    if hcr != 0.5:
        lines.append(f"• Студент выполнял это упражнение ранее: процент завершения {hcr:.0%}")
        apd = feats["avg_perceived_difficulty"]
        diff_words = {1:"очень лёгким",2:"лёгким",3:"умеренным",4:"сложным",5:"очень сложным"}
        lines.append(f"  Воспринимал как {diff_words.get(round(apd), 'умеренное')}")
    return "\n".join(lines)

def explain_plan_ru(student_id: int, weekly_plan: list,
                    model_path: str = "fitness_ranker.pkl") -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.student_name, s.age, s.gender,
               hp.medical_group_id, a.strength_score,
               a.endurance_score, a.flexibility_score, a."BMI"
        FROM students s
        JOIN students_health_profiles hp ON hp.student_id = s.student_id
        JOIN students_physical_readiness_assessments a ON a.health_profile_id = hp.health_profile_id
        WHERE s.student_id = %s LIMIT 1
    """, (student_id,))
    row = cur.fetchone()
    name, age, gender, mg_id, s_score, e_score, f_score, bmi = row
    cur.execute("""
        SELECT it.type_name, it.body_region, sih.recovery_status
        FROM student_injury_history sih
        JOIN injury_types it ON it.injury_type_id = sih.injury_type_id
        WHERE sih.student_id = %s AND sih.recovery_status = 'active'
    """, (student_id,))
    injuries = cur.fetchall()
    cur.close()
    conn.close()

    fitness_level = (float(s_score) + float(e_score) + float(f_score)) / 3
    gender_ru = "Мужской" if gender == "Male" else "Женский"

    lines = []
    lines.append("═" * 60)
    lines.append("ОБЪЯСНЕНИЕ ПЛАНА ТРЕНИРОВОК")
    lines.append(f"Студент: {name}, {age} лет, {gender_ru}")
    lines.append(f"Медицинская группа: {MEDICAL_GROUP_LABELS.get(mg_id, mg_id)}")
    lines.append(f"ИМТ: {float(bmi):.1f}")
    lines.append(f"Общий уровень подготовки: {_fitness_label(fitness_level)}  "
                 f"(сила {float(s_score):.1f} | выносливость {float(e_score):.1f} | гибкость {float(f_score):.1f})")
    if injuries:
        lines.append(f"\nАктивные травмы:")
        for inj_name, region, status in injuries:
            lines.append(f"  ⚠️  {inj_name} ({region}) — исключены все противопоказанные упражнения")
    else:
        lines.append("\nТравм нет — все упражнения доступны по состоянию здоровья")
    lines.append("\n" + "─" * 60)
    lines.append("ПОЧЕМУ ИМЕННО ТАКОЙ ПЛАН?\n")
    for session in weekly_plan:
        day_ru = {"MONDAY":"Понедельник","WEDNESDAY":"Среда","FRIDAY":"Пятница"}.get(session["day"], session["day"])
        focus_ru = {"strength":"силовая тренировка","cardio":"кардио и кор"}.get(session["focus"], session["focus"])
        lines.append(f"  {day_ru} — {focus_ru}")
        all_exs = session["warmup"] + session["main"] + session["cooldown"]
        for ex in all_exs:
            if ex in session["warmup"]: slot_ru = "разминка"
            elif ex in session["main"]: slot_ru = "основная часть"
            else: slot_ru = "заминка"
            score = ex.get("score", 0)
            diff_lbl = DIFFICULTY_LABELS.get(ex.get("difficulty", 3), " ")
            lines.append(f"    • {ex['exercise_name']: <28} [{slot_ru}]   "
                         f"сложность: {diff_lbl}  скор: {score:.0%}")
        lines.append(" ")
    lines.append("─" * 60)
    lines.append("ОБЩИЕ ПРИНЦИПЫ ПОСТРОЕНИЯ ПЛАНА:")
    lines.append("  1. Безопасность — исключены все упражнения, противопоказанные при травмах")
    lines.append("  2. Соответствие нагрузки — сложность подобрана под уровень физподготовки")
    lines.append("  3. Баланс мышечных групп — задействованы разные группы мышц по дням")
    lines.append("  4. Учёт истории — упражнения, которые студент выполнял успешно, получают приоритет")
    lines.append("═" * 60)
    return "\n".join(lines)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--student_id", type=int, default=1)
    parser.add_argument("--exercise_id", type=int, default=11)
    parser.add_argument("--mode", choices=["shap","ru","both"], default="both")
    args = parser.parse_args()
    if args.mode in ("shap","both"):
        print("\n── SHAP EXPLANATION ──────────────────────────────────")
        result = explain_exercise(args.student_id, args.exercise_id, plot=True)
        print(f"Score: {result['score']}")
        print("Top positive features:")
        for f, v in result["top_positive"]:
            print(f"  +{v:.4f}  {FEATURE_LABELS_RU.get(f, f)}")
        print("Top negative features:")
        for f, v in result["top_negative"]:
            print(f"  {v:.4f}  {FEATURE_LABELS_RU.get(f, f)}")
    if args.mode in ("ru","both"):
        print("\n── TEACHER EXPLANATION (RU) ──────────────────────────")
        print(explain_exercise_ru(args.student_id, args.exercise_id))