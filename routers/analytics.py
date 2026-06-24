from fastapi import APIRouter, HTTPException, Depends, Query
from feature_extractor import get_connection
from auth import get_current_user, get_current_student, get_current_teacher
from schemas import WorkoutFeedback

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/student/{student_id}/progression")
def get_student_progression(student_id: int, user: dict = Depends(get_current_user)):
    """View the dynamic of progression for a specific student"""
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    conn = get_connection()
    cur = conn.cursor()
    
    # Get workout history with completion stats
    cur.execute("""
        SELECT wp.date, wp.workout_status, wp.satisfaction,
               COUNT(ae.assigned_exercise_id) as total_exercises,
               COUNT(saei.assigned_exercise_interaction_id) as completed_exercises,
               AVG(CASE WHEN saei.completed THEN 1.0 ELSE 0.0 END) * 100 as completion_rate
        FROM workout_plan wp
        LEFT JOIN assigned_exercise ae ON ae.workout_plan_id = wp.workout_plan_id
        LEFT JOIN student_assigned_exercise_interaction saei ON saei.assigned_exercise_id = ae.assigned_exercise_id
        WHERE wp.student_id = %s
        GROUP BY wp.workout_plan_id, wp.date, wp.workout_status, wp.satisfaction
        ORDER BY wp.date DESC
        LIMIT 20
    """, (student_id,))
    
    workout_history = [{
        "date": str(r[0]),
        "status": r[1],
        "satisfaction": r[2],
        "total_exercises": r[3],
        "completed_exercises": r[4],
        "completion_rate": round(float(r[5]), 1) if r[5] else 0
    } for r in cur.fetchall()]
    
    # Get fitness metrics over time (if multiple assessments exist)
    cur.execute("""
        SELECT a.measurement_date, a.bmi, a.strength_score, a.endurance_score, a.flexibility_score
        FROM students_physical_readiness_assessments a
        JOIN students_health_profiles hp ON hp.health_profile_id = a.health_profile_id
        WHERE hp.student_id = %s
        ORDER BY a.measurement_date DESC
        LIMIT 10
    """, (student_id,))
    
    fitness_history = [{
        "date": str(r[0]),
        "bmi": float(r[1]) if r[1] else None,
        "strength_score": float(r[2]) if r[2] else None,
        "endurance_score": float(r[3]) if r[3] else None,
        "flexibility_score": float(r[4]) if r[4] else None
    } for r in cur.fetchall()]
    
    # Get exercise performance trends
    cur.execute("""
        SELECT e.exercise_name, 
               COUNT(saei.assigned_exercise_interaction_id) as attempts,
               AVG(CASE WHEN saei.completed THEN 1.0 ELSE 0.0 END) * 100 as completion_rate,
               AVG(saei.actually_sets::float / NULLIF(ae.recommended_sets, 0)) * 100 as sets_ratio
        FROM student_assigned_exercise_interaction saei
        JOIN assigned_exercise ae ON ae.assigned_exercise_id = saei.assigned_exercise_id
        JOIN exercises e ON e.exercise_id = ae.exercise_id
        WHERE saei.student_id = %s
        GROUP BY e.exercise_id, e.exercise_name
        ORDER BY completion_rate DESC
        LIMIT 15
    """, (student_id,))
    
    exercise_stats = [{
        "exercise": r[0],
        "attempts": r[1],
        "completion_rate": round(float(r[2]), 1) if r[2] else 0,
        "sets_ratio": round(float(r[3]), 1) if r[3] else 0
    } for r in cur.fetchall()]
    
    cur.close(); conn.close()
    
    return {
        "student_id": student_id,
        "workout_history": workout_history,
        "fitness_history": fitness_history,
        "exercise_stats": exercise_stats
    }

@router.get("/group/{group_id}/analytics")
def get_group_analytics(group_id: int, user: dict = Depends(get_current_teacher)):
    """View analytics of the group (best performing students, averages, etc.)"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Get group info
    cur.execute("SELECT group_name FROM groups WHERE group_id = %s", (group_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Group not found")
    group_name = row[0]
    
    # Get all students in this group with their overall stats
    cur.execute("""
        SELECT s.student_id, s.student_name,
               COUNT(DISTINCT wp.workout_plan_id) as total_workouts,
               COUNT(DISTINCT CASE WHEN wp.workout_status = 'COMPLETED' THEN wp.workout_plan_id END) as completed_workouts,
               AVG(CASE WHEN saei.completed THEN 1.0 ELSE 0.0 END) * 100 as overall_completion_rate,
               AVG(CASE 
                   WHEN saei.perceived_difficulty = 'Very Easy' THEN 1
                   WHEN saei.perceived_difficulty = 'Easy' THEN 2
                   WHEN saei.perceived_difficulty = 'Normal' THEN 3
                   WHEN saei.perceived_difficulty = 'Hard' THEN 4
                   WHEN saei.perceived_difficulty = 'Very Hard' THEN 5
                   ELSE NULL END) as avg_difficulty
        FROM students s
        LEFT JOIN workout_plan wp ON wp.student_id = s.student_id
        LEFT JOIN assigned_exercise ae ON ae.workout_plan_id = wp.workout_plan_id
        LEFT JOIN student_assigned_exercise_interaction saei ON saei.assigned_exercise_id = ae.assigned_exercise_id
        WHERE s.group_id = %s
        GROUP BY s.student_id, s.student_name
        ORDER BY overall_completion_rate DESC
    """, (group_id,))
    
    student_stats = []
    for r in cur.fetchall():
        student_stats.append({
            "student_id": r[0],
            "name": r[1],
            "total_workouts": r[2],
            "completed_workouts": r[3],
            "completion_rate": round(float(r[4]), 1) if r[4] else 0,
            "avg_difficulty": round(float(r[5]), 1) if r[5] else None
        })
    
    # Calculate group averages
    if student_stats:
        avg_completion = sum(s["completion_rate"] for s in student_stats) / len(student_stats)
        best_students = sorted(student_stats, key=lambda x: x["completion_rate"], reverse=True)[:5]
    else:
        avg_completion = 0
        best_students = []
    
    # Get most common injuries in the group
    cur.execute("""
        SELECT it.type_name, COUNT(*) as count
        FROM student_injury_history sih
        JOIN injury_types it ON it.injury_type_id = sih.injury_type_id
        JOIN students s ON s.student_id = sih.student_id
        WHERE s.group_id = %s AND sih.recovery_status = 'active'
        GROUP BY it.injury_type_id, it.type_name
        ORDER BY count DESC
    """, (group_id,))
    
    common_injuries = [{"type": r[0], "count": r[1]} for r in cur.fetchall()]
    
    cur.close(); conn.close()
    
    return {
        "group_id": group_id,
        "group_name": group_name,
        "total_students": len(student_stats),
        "average_completion_rate": round(avg_completion, 1),
        "best_performing_students": best_students,
        "all_students": student_stats,
        "common_injuries": common_injuries
    }

@router.get("/groups")
def get_all_groups(user: dict = Depends(get_current_user)):
    """Get all groups (for teacher to view)"""
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT g.group_id, g.group_name, COUNT(s.student_id) as student_count
        FROM groups g
        LEFT JOIN students s ON s.group_id = g.group_id
        GROUP BY g.group_id, g.group_name
        ORDER BY g.group_name
    """)
    
    rows = cur.fetchall()
    cur.close(); conn.close()
    
    return {
        "groups": [{
            "group_id": r[0],
            "group_name": r[1],
            "student_count": r[2]
        } for r in rows]
    }

@router.post("/plan/{plan_id}/feedback")
def submit_workout_feedback(plan_id: int, feedback: WorkoutFeedback, user: dict = Depends(get_current_user)):
    """Submit feedback for a completed workout"""
    conn = get_connection()
    cur = conn.cursor()
    
    # Verify ownership
    cur.execute("SELECT student_id FROM workout_plan WHERE workout_plan_id = %s", (plan_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="Plan not found")
    
    student_id = row[0]
    if user["role"] == "student" and user["student_id"] != student_id:
        cur.close(); conn.close()
        raise HTTPException(status_code=403, detail="Can only provide feedback for your own workouts")
    
    # Update the plan with feedback
    cur.execute("""
        UPDATE workout_plan 
        SET satisfaction = %s, feedback_notes = %s
        WHERE workout_plan_id = %s
        RETURNING workout_plan_id
    """, (feedback.satisfaction, feedback.feedback_notes, plan_id))
    
    cur.fetchone()
    conn.commit()
    cur.close(); conn.close()
    
    return {"success": True, "plan_id": plan_id, "message": "Feedback submitted successfully"}
