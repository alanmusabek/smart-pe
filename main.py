"""
main.py — FastAPI backend for Smart PE recommendation system
Run: uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
import joblib
import os
from feature_extractor import get_connection
from plan_assembler import generate_plan
from explainability import (
    explain_exercise, explain_exercise_ru,
    explain_plan_ru, explain_plan_shap,
    FEATURE_LABELS_RU,
)
from retrain import run_retrain, check_readiness, retrain_history
from auth import router as auth_router, get_current_user, get_current_student, get_current_teacher

app = FastAPI(
    title="Smart PE — Workout Recommendation API",
    description="AI-powered physical education workout planner",
    version="1.0.0",
)

# Include auth router
app.include_router(auth_router)

MODEL_PATH = "fitness_ranker.pkl"

# ── Pydantic schemas ────────────────────────────────────────────────────────
class PlanRequest(BaseModel):
    student_id: int
    save_to_db: bool = True

class InteractionUpdate(BaseModel):
    assigned_exercise_id: int
    completed: bool
    actually_sets: Optional[int] = None
    actually_reps: Optional[int] = None
    perceived_difficulty: Optional[str] = Field(
        None, description="Very Easy | Easy | Normal | Hard | Very Hard"
    )
    feedback_notes: Optional[str] = None
    exercise_status: str = Field(
        "COMPLETED", description="COMPLETED | SKIPPED | DISCARDED | IN_PROGRESS"
    )

class PlanStatusUpdate(BaseModel):
    workout_plan_id: int
    workout_status: str = Field(description="COMPLETED | DISCARDED | SKIPPED | IN_PROGRESS")
    satisfaction: Optional[str] = Field(None, description="Liked | Disliked")

class RetrainRequest(BaseModel):
    force: bool = False

# ── /students ───────────────────────────────────────────────────────────────
@app.get("/students/{student_id}", tags=["Students"])
def get_student(student_id: int, user: dict = Depends(get_current_user)):
    """Get student profile. Students can only view their own profile."""
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.student_id, s.student_name, s.age, s.gender,
               hp.medical_group_id, mg.group_name,
               hp.height_cm, hp.weight_kg,
               hp.cooper_meters, hp.push_ups, hp.pull_ups,
               hp.flexibility_cm, hp.sit_ups, hp.jump_forward,
               hp.measurement_date,
               a.bmi, a.strength_score, a.endurance_score, a.flexibility_score
        FROM students s
        JOIN students_health_profiles hp ON hp.student_id = s.student_id
        JOIN medical_group mg ON mg.group_id = hp.medical_group_id
        JOIN students_physical_readiness_assessments a ON a.health_profile_id = hp.health_profile_id
        WHERE s.student_id = %s LIMIT 1
    """, (student_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
    cur.execute("""
        SELECT it.type_name, it.body_region, sih.recovery_status, sih.recovery_date
        FROM student_injury_history sih
        JOIN injury_types it ON it.injury_type_id = sih.injury_type_id
        WHERE sih.student_id = %s AND sih.recovery_status = 'active'
    """, (student_id,))
    injuries = [
        {"type": r[0], "region": r[1], "status": r[2], "recovery_date": str(r[3])}
        for r in cur.fetchall()
    ]
    cur.close(); conn.close()
    return {
        "student_id": row[0], "name": row[1], "age": row[2], "gender": row[3],
        "medical_group_id": row[4], "medical_group": row[5],
        "biometrics": {"height_cm": row[6], "weight_kg": row[7], "bmi": float(row[15])},
        "fitness_metrics": {
            "cooper_meters": row[8], "push_ups": row[9], "pull_ups": row[10],
            "flexibility": row[11], "sit_ups": row[12], "jump_forward": row[13],
        },
        "assessment_scores": {
            "strength": float(row[16]), "endurance": float(row[17]), "flexibility": float(row[18]),
        },
        "measurement_date": str(row[14]),
        "active_injuries": injuries,
    }

@app.get("/students/me", tags=["Students"])
def get_my_profile(user: dict = Depends(get_current_student)):
    """Get current student's profile (shortcut)."""
    return get_student(user["student_id"], user)

@app.get("/students/{student_id}/muscle-fatigue", tags=["Students"])
def get_muscle_fatigue(student_id: int, user: dict = Depends(get_current_user)):
    """Get current muscle fatigue status for a student."""
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT mg.muscle_name, mf.recovery_left, mf.recovery_hours,
               mf.status, mf.date
        FROM muscle_fatigue mf
        JOIN assigned_exercise_muscle_group aemg
            ON aemg.assigned_exercise_muscle_group_id = mf.assigned_exercise_muscle_group_id
        JOIN muscle_group mg ON mg.muscle_group_id = aemg.muscle_group_id
        WHERE mf.student_id = %s AND mf.status = 'ACTIVE'
        ORDER BY mf.recovery_left DESC
    """, (student_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return {
        "student_id": student_id,
        "active_fatigue": [
            {
                "muscle": r[0],
                "recovery_left_h": round(float(r[1]), 1),
                "recovery_total_h": round(float(r[2]), 1),
                "recovery_pct": round((1 - float(r[1])/float(r[2]))*100, 1),
                "since_date": str(r[4]),
            }
            for r in rows
        ]
    }

# ── /plans ──────────────────────────────────────────────────────────────────
@app.post("/plans/generate", tags=["Plans"])
def generate_workout_plan(request: PlanRequest, user: dict = Depends(get_current_user)):
    """Generate and optionally save a personalized weekly workout plan."""
    if user["role"] == "student" and user["student_id"] != request.student_id:
        raise HTTPException(status_code=403, detail="Can only generate plans for yourself")
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=503, detail="Model not found. Run train_model.py first.")
    try:
        weekly_plan = generate_plan(student_id=request.student_id, save_to_db=request.save_to_db)
        return {"student_id": request.student_id, "saved_to_db": request.save_to_db, "plan": weekly_plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/plans/{student_id}/history", tags=["Plans"])
def get_plan_history(student_id: int, limit: int = Query(10, ge=1, le=50),
                     user: dict = Depends(get_current_user)):
    """Get past workout plans for a student."""
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT workout_plan_id, date, workout_status, satisfaction
        FROM workout_plan WHERE student_id = %s ORDER BY date DESC LIMIT %s
    """, (student_id, limit))
    plans = [{"plan_id": r[0], "date": str(r[1]), "status": r[2], "satisfaction": r[3]} for r in cur.fetchall()]
    cur.close(); conn.close()
    return {"student_id": student_id, "plans": plans}

@app.get("/plans/{plan_id}/exercises", tags=["Plans"])
def get_plan_exercises(plan_id: int, user: dict = Depends(get_current_user)):
    """Get all assigned exercises for a workout plan."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ae.assigned_exercise_id, e.exercise_name, ae.slot_type,
               ae.day_of_week, ae.order_in_session, ae.predicted_score,
               ae.recommended_sets, ae.recommended_reps,
               COALESCE(saei.exercise_status, 'SCHEDULED') AS status,
               saei.completed, saei.actually_sets, saei.actually_reps,
               saei.perceived_difficulty
        FROM assigned_exercise ae
        JOIN exercises e ON e.exercise_id = ae.exercise_id
        LEFT JOIN student_assigned_exercise_interaction saei
            ON saei.assigned_exercise_id = ae.assigned_exercise_id
        WHERE ae.workout_plan_id = %s
        ORDER BY ae.day_of_week, ae.order_in_session
    """, (plan_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    if not rows:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id} not found")
    return {
        "plan_id": plan_id,
        "exercises": [
            {
                "assigned_exercise_id": r[0], "exercise_name": r[1], "slot_type": r[2],
                "day_of_week": r[3], "order": r[4],
                "predicted_score": float(r[5]) if r[5] else None,
                "recommended_sets": r[6], "recommended_reps": r[7],
                "status": r[8], "completed": r[9],
                "actually_sets": r[10], "actually_reps": r[11],
                "perceived_difficulty": r[12],
            }
            for r in rows
        ]
    }

@app.patch("/plans/status", tags=["Plans"])
def update_plan_status(update: PlanStatusUpdate, user: dict = Depends(get_current_user)):
    """Update overall workout session status and satisfaction."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE workout_plan SET workout_status = %s, satisfaction = %s
        WHERE workout_plan_id = %s RETURNING workout_plan_id
    """, (update.workout_status, update.satisfaction, update.workout_plan_id))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Plan not found")
    conn.commit(); cur.close(); conn.close()
    return {"updated": True, "plan_id": update.workout_plan_id}

# ── /interactions ───────────────────────────────────────────────────────────
@app.post("/interactions", tags=["Interactions"])
def record_interaction(update: InteractionUpdate, user: dict = Depends(get_current_student)):
    """Record student interaction with an assigned exercise."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT wp.student_id, ae.workout_plan_id
        FROM assigned_exercise ae
        JOIN workout_plan wp ON wp.workout_plan_id = ae.workout_plan_id
        WHERE ae.assigned_exercise_id = %s
    """, (update.assigned_exercise_id,))
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Assigned exercise not found")
    student_id, plan_id = row
    if user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Can only record your own interactions")

    cur.execute("""
        INSERT INTO student_assigned_exercise_interaction
            (student_id, workout_plan_id, assigned_exercise_id, completed,
             actually_sets, actually_reps, perceived_difficulty,
             feedback_notes, interaction_date, exercise_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE, %s)
        ON CONFLICT DO NOTHING
        RETURNING assigned_exercise_interaction_id
    """, (student_id, plan_id, update.assigned_exercise_id,
          update.completed, update.actually_sets, update.actually_reps,
          update.perceived_difficulty, update.feedback_notes, update.exercise_status))
    new_id = cur.fetchone()
    if update.completed and update.exercise_status == "COMPLETED":
        cur.execute("""
            UPDATE muscle_fatigue SET status = 'ACTIVE'
            WHERE assigned_exercise_id = %s
        """, (update.assigned_exercise_id,))
    conn.commit(); cur.close(); conn.close()
    return {"recorded": True, "interaction_id": new_id[0] if new_id else None, "student_id": student_id}

@app.get("/interactions/{student_id}/summary", tags=["Interactions"])
def get_interaction_summary(student_id: int, user: dict = Depends(get_current_user)):
    """Get interaction statistics for a student."""
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT e.exercise_name, e.category_id,
               COUNT(*) AS attempts,
               AVG(CASE WHEN saei.completed THEN 1.0 ELSE 0.0 END) AS completion_rate,
               AVG(CASE
                   WHEN saei.perceived_difficulty = 'Very Easy' THEN 1
                   WHEN saei.perceived_difficulty = 'Easy' THEN 2
                   WHEN saei.perceived_difficulty = 'Normal' THEN 3
                   WHEN saei.perceived_difficulty = 'Hard' THEN 4
                   WHEN saei.perceived_difficulty = 'Very Hard' THEN 5
                   ELSE NULL END) AS avg_difficulty,
               AVG(saei.actually_sets::float / NULLIF(ae.recommended_sets,0)) AS set_ratio
        FROM student_assigned_exercise_interaction saei
        JOIN assigned_exercise ae ON ae.assigned_exercise_id = saei.assigned_exercise_id
        JOIN exercises e ON e.exercise_id = ae.exercise_id
        WHERE saei.student_id = %s
        GROUP BY e.exercise_id, e.exercise_name, e.category_id
        ORDER BY completion_rate DESC
    """, (student_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return {
        "student_id": student_id,
        "exercise_stats": [
            {
                "exercise": r[0], "attempts": r[2],
                "completion_rate": round(float(r[3]), 2) if r[3] else None,
                "avg_difficulty": round(float(r[4]), 1) if r[4] else None,
                "set_ratio": round(float(r[5]), 2) if r[5] else None,
            }
            for r in rows
        ]
    }

# ── /model ──────────────────────────────────────────────────────────────────
@app.get("/model/status", tags=["Model"])
def model_status(user: dict = Depends(get_current_teacher)):
    """Get current model status (teacher only)."""
    exists = os.path.exists(MODEL_PATH)
    ready = check_readiness() if exists else {"ready": False}
    history = retrain_history()
    last = history[-1] if history else None
    return {
        "model_loaded": exists, "model_path": MODEL_PATH,
        "retrain_ready": ready.get("ready", False),
        "new_interactions": ready.get("new_interactions", 0),
        "threshold": ready.get("threshold", 200),
        "last_retrain": last,
        "total_retrains": len([e for e in history if e.get("status") == "replaced"]),
    }

@app.post("/model/retrain", tags=["Model"])
def trigger_retrain(request: RetrainRequest, background_tasks: BackgroundTasks,
                    user: dict = Depends(get_current_teacher)):
    """Trigger model retraining (teacher only)."""
    if not request.force:
        readiness = check_readiness()
        if not readiness["ready"]:
            return {"started": False,
                    "reason": f"Not enough new data ({readiness['new_interactions']} / {readiness['threshold']}). Use force=true to override."}
    background_tasks.add_task(run_retrain, force=request.force)
    return {"started": True, "message": "Retraining started in background.", "forced": request.force}

@app.get("/model/retrain/history", tags=["Model"])
def get_retrain_history(user: dict = Depends(get_current_teacher)):
    """Get full model retraining history (teacher only)."""
    return {"history": retrain_history()}

# ── /explain ────────────────────────────────────────────────────────────────
@app.get("/explain/exercise/{student_id}/{exercise_id}", tags=["Explainability"])
def explain_exercise_endpoint(student_id: int, exercise_id: int,
                              user: dict = Depends(get_current_user)):
    """SHAP explanation for one (student, exercise) pair."""
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=503, detail="Model not found")
    try:
        result = explain_exercise(student_id, exercise_id)
        result["shap_values_labeled"] = {
            FEATURE_LABELS_RU.get(f, f): v for f, v in result["shap_values"].items()
        }
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/explain/exercise/{student_id}/{exercise_id}/ru", tags=["Explainability"])
def explain_exercise_ru_endpoint(student_id: int, exercise_id: int,
                                 user: dict = Depends(get_current_user)):
    """Human-readable Russian explanation for a (student, exercise) recommendation."""
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=503, detail="Model not found")
    try:
        text = explain_exercise_ru(student_id, exercise_id)
        return {"student_id": student_id, "exercise_id": exercise_id, "explanation": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/explain/plan/{student_id}/ru", tags=["Explainability"])
def explain_plan_ru_endpoint(student_id: int, user: dict = Depends(get_current_user)):
    """Generate and explain a weekly plan in human-readable Russian."""
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=503, detail="Model not found")
    try:
        weekly_plan = generate_plan(student_id, save_to_db=False)
        explanation = explain_plan_ru(student_id, weekly_plan)
        return {"student_id": student_id, "plan": weekly_plan, "explanation": explanation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/explain/plan/{student_id}/shap-plot", tags=["Explainability"])
def explain_plan_shap_plot(student_id: int, user: dict = Depends(get_current_user)):
    """Generate SHAP summary plot for a student's weekly plan."""
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=503, detail="Model not found")
    try:
        plot_path = f"shap_plan_{student_id}.png"
        weekly_plan = generate_plan(student_id, save_to_db=False)
        explain_plan_shap(student_id, weekly_plan, plot_path=plot_path)
        return FileResponse(plot_path, media_type="image/png",
                            filename=f"shap_plan_student_{student_id}.png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Health check ────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Smart PE Recommendation API",
        "version": "1.0.0",
        "model_ready": os.path.exists(MODEL_PATH),
        "docs": "/docs",
    }