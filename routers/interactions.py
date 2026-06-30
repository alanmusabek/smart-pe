from fastapi import APIRouter, HTTPException, Depends
from feature_extractor import get_connection
from auth import get_current_user, get_current_student, get_current_teacher
from schemas import InteractionUpdate, InteractionEdit

router = APIRouter(prefix="/interactions", tags=["Interactions"])

@router.post("/")
def record_interaction(update: InteractionUpdate, user: dict = Depends(get_current_student)):
    """Mark an exercise as completed/skipped with actual performance data"""
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""
        SELECT wp.student_id, ae.workout_plan_id FROM assigned_exercise ae
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
            (student_id, workout_plan_id, assigned_exercise_id, completed, actually_sets, actually_reps, 
             perceived_difficulty, feedback_notes, interaction_date, exercise_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, CURRENT_DATE, %s)
        ON CONFLICT (assigned_exercise_id, student_id) DO UPDATE SET
            completed = EXCLUDED.completed,
            actually_sets = EXCLUDED.actually_sets,
            actually_reps = EXCLUDED.actually_reps,
            perceived_difficulty = EXCLUDED.perceived_difficulty,
            feedback_notes = EXCLUDED.feedback_notes,
            exercise_status = EXCLUDED.exercise_status,
            interaction_date = CURRENT_DATE
        RETURNING assigned_exercise_interaction_id
    """, (student_id, plan_id, update.assigned_exercise_id, update.completed, update.actually_sets, 
          update.actually_reps, update.perceived_difficulty, update.feedback_notes, update.exercise_status))
    new_id = cur.fetchone()
    if update.completed and update.exercise_status == "COMPLETED":
        cur.execute("UPDATE muscle_fatigue SET status = 'ACTIVE' WHERE assigned_exercise_id = %s", (update.assigned_exercise_id,))
    conn.commit(); cur.close(); conn.close()
    return {"recorded": True, "interaction_id": new_id[0] if new_id else None, "student_id": student_id}

@router.get("/{student_id}/summary")
def get_interaction_summary(student_id: int, user: dict = Depends(get_current_user)):
    """Get summary of student's exercise interactions"""
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
    """Teacher can edit a student's interaction (sets/reps/difficulty)"""
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

@router.post("/exercise/{assigned_exercise_id}/feedback")
def submit_exercise_feedback(assigned_exercise_id: int, feedback_notes: str, user: dict = Depends(get_current_student)):
    """Student provides feedback for a specific exercise"""
    conn = get_connection(); cur = conn.cursor()
    
    # Verify ownership
    cur.execute("""
        SELECT ae.assigned_exercise_id, wp.student_id 
        FROM assigned_exercise ae
        JOIN workout_plan wp ON wp.workout_plan_id = ae.workout_plan_id
        WHERE ae.assigned_exercise_id = %s
    """, (assigned_exercise_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Exercise not found")
    
    ex_id, student_id = row
    if user["student_id"] != student_id:
        cur.close(); conn.close()
        raise HTTPException(status_code=403, detail="Can only provide feedback for your own exercises")
    
    # Update or insert feedback
    cur.execute("""
        INSERT INTO student_assigned_exercise_interaction
            (student_id, workout_plan_id, assigned_exercise_id, feedback_notes, interaction_date)
        SELECT wp.student_id, wp.workout_plan_id, %s, %s, CURRENT_DATE
        FROM assigned_exercise ae
        JOIN workout_plan wp ON wp.workout_plan_id = ae.workout_plan_id
        WHERE ae.assigned_exercise_id = %s
        ON CONFLICT (assigned_exercise_id, student_id) DO UPDATE SET
            feedback_notes = EXCLUDED.feedback_notes,
            interaction_date = CURRENT_DATE
        RETURNING assigned_exercise_interaction_id
    """, (assigned_exercise_id, feedback_notes, assigned_exercise_id))
    
    interaction_id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    return {"success": True, "interaction_id": interaction_id, "message": "Exercise feedback saved"}