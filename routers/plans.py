import os
from fastapi import APIRouter, HTTPException, Depends, Query
from feature_extractor import get_connection
from plan_assembler import generate_plan
from auth import get_current_user, get_current_teacher
from schemas import PlanRequest, PlanStatusUpdate, ExerciseUpdate, ExerciseCreate

router = APIRouter(prefix="/plans", tags=["Plans"])
MODEL_PATH = "fitness_ranker.pkl"

@router.post("/generate")
def generate_workout_plan(request: PlanRequest, user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["student_id"] != request.student_id:
        raise HTTPException(status_code=403, detail="Can only generate plans for yourself")
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=503, detail="Model not found. Run train_model.py first.")
    try:
        weekly_plan = generate_plan(student_id=request.student_id, save_to_db=request.save_to_db)
        return {"student_id": request.student_id, "saved_to_db": request.save_to_db, "plan": weekly_plan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{student_id}/history")
def get_plan_history(student_id: int, limit: int = Query(10, ge=1, le=50), user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT workout_plan_id, date, workout_status, satisfaction FROM workout_plan WHERE student_id = %s ORDER BY date DESC LIMIT %s", (student_id, limit))
    plans = [{"plan_id": r[0], "date": str(r[1]), "status": r[2], "satisfaction": r[3]} for r in cur.fetchall()]
    cur.close(); conn.close()
    return {"student_id": student_id, "plans": plans}

@router.get("/{plan_id}/exercises")
def get_plan_exercises(plan_id: int, user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT student_id FROM workout_plan WHERE workout_plan_id = %s", (plan_id,))
    owner = cur.fetchone()
    if owner is None:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Plan not found")
    if user["role"] == "student" and user["student_id"] != owner[0]:
        cur.close(); conn.close()
        raise HTTPException(status_code=403, detail="Access denied")
    cur.execute("""
        SELECT ae.assigned_exercise_id, e.exercise_id, e.exercise_name, ae.slot_type,
               ae.day_of_week, ae.order_in_session, ae.predicted_score, ae.recommended_sets, ae.recommended_reps,
               COALESCE(saei.exercise_status, 'SCHEDULED') AS status, saei.completed, saei.actually_sets, 
               saei.actually_reps, saei.perceived_difficulty
        FROM assigned_exercise ae
        JOIN exercises e ON e.exercise_id = ae.exercise_id
        LEFT JOIN LATERAL (
            SELECT * FROM student_assigned_exercise_interaction i
            WHERE i.assigned_exercise_id = ae.assigned_exercise_id
            ORDER BY i.assigned_exercise_interaction_id DESC LIMIT 1
        ) saei ON TRUE
        WHERE ae.workout_plan_id = %s
        ORDER BY ae.day_of_week, ae.order_in_session
    """, (plan_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return {
        "plan_id": plan_id,
        "exercises": [{
            "assigned_exercise_id": r[0], "exercise_id": r[1], "exercise_name": r[2], "slot_type": r[3],
            "day_of_week": r[4], "order": r[5], "predicted_score": float(r[6]) if r[6] else None,
            "recommended_sets": r[7], "recommended_reps": r[8], "status": r[9], "completed": r[10],
            "actually_sets": r[11], "actually_reps": r[12], "perceived_difficulty": r[13],
        } for r in rows]
    }

@router.patch("/status")
def update_plan_status(update: PlanStatusUpdate, user: dict = Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE workout_plan SET workout_status = %s, satisfaction = %s
        WHERE workout_plan_id = %s AND (%s = 'teacher' OR student_id = %s)
        RETURNING workout_plan_id
    """, (update.workout_status, update.satisfaction, update.workout_plan_id,
          user["role"], user["student_id"]))
    if not cur.fetchone():
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Plan not found")
    conn.commit(); cur.close(); conn.close()
    return {"updated": True, "plan_id": update.workout_plan_id}

# --- Teacher Endpoints ---
@router.delete("/{plan_id}", tags=["Teacher"])
def delete_workout_plan(plan_id: int, user: dict = Depends(get_current_teacher)):
    """Delete one scheduled workout and its dependent records atomically."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT workout_status FROM workout_plan WHERE workout_plan_id = %s FOR UPDATE", (plan_id,))
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Workout not found")
        if row[0] != "SCHEDULED":
            raise HTTPException(status_code=409, detail="Only scheduled workouts can be deleted")

        cur.execute("DELETE FROM muscle_fatigue WHERE workout_plan_id = %s", (plan_id,))
        cur.execute("DELETE FROM student_assigned_exercise_interaction WHERE workout_plan_id = %s", (plan_id,))
        cur.execute("""
            DELETE FROM assigned_exercise_muscle_group
            WHERE assigned_exercise_id IN (
                SELECT assigned_exercise_id FROM assigned_exercise WHERE workout_plan_id = %s
            )
        """, (plan_id,))
        cur.execute("DELETE FROM assigned_exercise WHERE workout_plan_id = %s", (plan_id,))
        cur.execute("DELETE FROM workout_plan WHERE workout_plan_id = %s", (plan_id,))
        conn.commit()
        return {"deleted": True, "plan_id": plan_id}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

@router.patch("/{plan_id}/exercises/{assigned_exercise_id}", tags=["Teacher"])
def update_plan_exercise(plan_id: int, assigned_exercise_id: int, update: ExerciseUpdate, user: dict = Depends(get_current_teacher)):
    conn = get_connection(); cur = conn.cursor()
    updates, values = [], []
    for field, value in update.dict(exclude_none=True).items():
        updates.append(f"{field} = %s"); values.append(value)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    values.extend([assigned_exercise_id, plan_id])
    cur.execute(f"UPDATE assigned_exercise SET {', '.join(updates)} WHERE assigned_exercise_id = %s AND workout_plan_id = %s RETURNING assigned_exercise_id", values)
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Exercise not found in plan")
    conn.commit(); cur.close(); conn.close()
    return {"updated": True}

@router.delete("/{plan_id}/exercises/{assigned_exercise_id}", tags=["Teacher"])
def delete_plan_exercise(plan_id: int, assigned_exercise_id: int, user: dict = Depends(get_current_teacher)):
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("""
            SELECT assigned_exercise_id FROM assigned_exercise
            WHERE assigned_exercise_id = %s AND workout_plan_id = %s FOR UPDATE
        """, (assigned_exercise_id, plan_id))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Exercise not found in plan")
        cur.execute("DELETE FROM muscle_fatigue WHERE assigned_exercise_id = %s", (assigned_exercise_id,))
        cur.execute("DELETE FROM student_assigned_exercise_interaction WHERE assigned_exercise_id = %s", (assigned_exercise_id,))
        cur.execute("DELETE FROM assigned_exercise_muscle_group WHERE assigned_exercise_id = %s", (assigned_exercise_id,))
        cur.execute("DELETE FROM assigned_exercise WHERE assigned_exercise_id = %s", (assigned_exercise_id,))
        conn.commit()
        return {"deleted": True}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

@router.post("/{plan_id}/exercises", tags=["Teacher"])
def add_exercise_to_plan(plan_id: int, exercise: ExerciseCreate, user: dict = Depends(get_current_teacher)):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        INSERT INTO assigned_exercise (workout_plan_id, exercise_id, slot_type, day_of_week, order_in_session, recommended_sets, recommended_reps)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING assigned_exercise_id
    """, (plan_id, exercise.exercise_id, exercise.slot_type, exercise.day_of_week, exercise.order_in_session, exercise.recommended_sets, exercise.recommended_reps))
    new_id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    return {"created": True, "assigned_exercise_id": new_id}
