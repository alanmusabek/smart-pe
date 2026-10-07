from fastapi import APIRouter, HTTPException, Depends
from feature_extractor import get_connection
from auth import get_current_user, get_current_student, get_current_teacher
from schemas import InteractionUpdate, InteractionEdit

router = APIRouter(prefix="/interactions", tags=["Interactions"])

@router.post("/")
def record_interaction(update: InteractionUpdate, user: dict = Depends(get_current_student)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Serialize submissions for one assignment, including the first insert.
        cur.execute("""
            SELECT wp.student_id, ae.workout_plan_id FROM assigned_exercise ae
            JOIN workout_plan wp ON wp.workout_plan_id = ae.workout_plan_id
            WHERE ae.assigned_exercise_id = %s FOR UPDATE OF ae
        """, (update.assigned_exercise_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Assigned exercise not found")
        student_id, plan_id = row
        if user["student_id"] != student_id:
            raise HTTPException(status_code=403, detail="Can only record your own interactions")
        cur.execute("""
            SELECT assigned_exercise_interaction_id
            FROM student_assigned_exercise_interaction
            WHERE assigned_exercise_id = %s AND student_id = %s
            ORDER BY assigned_exercise_interaction_id DESC LIMIT 1
        """, (update.assigned_exercise_id, student_id))
        previous = cur.fetchone()
        fields = (update.completed, update.actually_sets, update.actually_reps,
                  update.perceived_difficulty, update.feedback_notes, update.exercise_status)
        if previous:
            cur.execute("""
                UPDATE student_assigned_exercise_interaction
                SET completed=%s, actually_sets=%s, actually_reps=%s,
                    perceived_difficulty=%s, feedback_notes=%s, exercise_status=%s,
                    interaction_date=CURRENT_DATE
                WHERE assigned_exercise_interaction_id=%s
                RETURNING assigned_exercise_interaction_id
            """, (*fields, previous[0]))
        else:
            cur.execute("""
                INSERT INTO student_assigned_exercise_interaction
                    (completed, actually_sets, actually_reps, perceived_difficulty,
                     feedback_notes, exercise_status, student_id, workout_plan_id,
                     assigned_exercise_id, interaction_date)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,CURRENT_DATE)
                RETURNING assigned_exercise_interaction_id
            """, (*fields, student_id, plan_id, update.assigned_exercise_id))
        interaction_id = cur.fetchone()[0]
        if update.completed and update.exercise_status == "COMPLETED":
            cur.execute("UPDATE muscle_fatigue SET status = 'ACTIVE' WHERE assigned_exercise_id = %s", (update.assigned_exercise_id,))
        conn.commit()
        return {"recorded": True, "interaction_id": interaction_id, "student_id": student_id}
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

@router.get("/{student_id}/summary")
def get_interaction_summary(student_id: int, user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT e.exercise_name, e.category_id, COUNT(*) AS attempts,
               AVG(CASE WHEN saei.completed THEN 1.0 ELSE 0.0 END) AS completion_rate,
               AVG(CASE WHEN saei.perceived_difficulty = 'Very Easy' THEN 1 WHEN saei.perceived_difficulty = 'Easy' THEN 2
                        WHEN saei.perceived_difficulty = 'Normal' THEN 3 WHEN saei.perceived_difficulty = 'Hard' THEN 4
                        WHEN saei.perceived_difficulty = 'Very Hard' THEN 5 ELSE NULL END) AS avg_difficulty,
               AVG(saei.actually_sets::float / NULLIF(ae.recommended_sets,0)) AS set_ratio
        FROM student_assigned_exercise_interaction saei
        JOIN assigned_exercise ae ON ae.assigned_exercise_id = saei.assigned_exercise_id
        JOIN exercises e ON e.exercise_id = ae.exercise_id
        WHERE saei.student_id = %s
        GROUP BY e.exercise_id, e.exercise_name, e.category_id
        ORDER BY completion_rate DESC
    """, (student_id,))
    rows = cur.fetchall(); cur.close(); conn.close()
    return {
        "student_id": student_id,
        "exercise_stats": [{
            "exercise": r[0], "attempts": r[2],
            "completion_rate": round(float(r[3]), 2) if r[3] else None,
            "avg_difficulty": round(float(r[4]), 1) if r[4] else None,
            "set_ratio": round(float(r[5]), 2) if r[5] else None,
        } for r in rows]
    }

@router.patch("/{interaction_id}", tags=["Teacher"])
def edit_interaction(interaction_id: int, update: InteractionEdit, user: dict = Depends(get_current_teacher)):
    conn = get_connection(); cur = conn.cursor()
    updates, values = [], []
    for field, value in update.dict(exclude_none=True).items():
        updates.append(f"{field} = %s"); values.append(value)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    values.append(interaction_id)
    cur.execute(f"UPDATE student_assigned_exercise_interaction SET {', '.join(updates)} WHERE assigned_exercise_interaction_id = %s RETURNING assigned_exercise_interaction_id", values)
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Interaction not found")
    conn.commit(); cur.close(); conn.close()
    return {"updated": True}
