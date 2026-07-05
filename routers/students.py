from fastapi import APIRouter, HTTPException, Depends
from feature_extractor import get_connection
from auth import get_current_user, get_current_student, get_current_teacher
from schemas import HealthProfileUpdate, InjuryCreate, InjuryUpdate, MuscleFatigueUpdate

router = APIRouter(prefix="/students", tags=["Students"])

@router.get("/me")
def get_my_profile(user: dict = Depends(get_current_student)):
    return get_student(user["student_id"], user)

@router.get("/{student_id}")
def get_student(student_id: int, user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.student_id, s.student_name, s.age, s.gender,
               hp.medical_group_id, mg.group_name, hp.height_cm, hp.weight_kg,
               hp.cooper_meters, hp.push_ups, hp.pull_ups, hp.flexibility_cm, 
               hp.sit_ups, hp.jump_forward, hp.measurement_date, a."BMI", 
               a.strength_score, a.endurance_score, a.flexibility_score
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
    injuries = [{"type": r[0], "region": r[1], "status": r[2], "recovery_date": str(r[3])} for r in cur.fetchall()]
    cur.close(); conn.close()
    
    return {
        "student_id": row[0], "name": row[1], "age": row[2], "gender": row[3],
        "medical_group_id": row[4], "medical_group": row[5],
        "biometrics": {"height_cm": row[6], "weight_kg": row[7], "bmi": float(row[15])},
        "fitness_metrics": {"cooper_meters": row[8], "push_ups": row[9], "pull_ups": row[10],
                            "flexibility": row[11], "sit_ups": row[12], "jump_forward": row[13]},
        "assessment_scores": {"strength": float(row[16]), "endurance": float(row[17]), "flexibility": float(row[18])},
        "measurement_date": str(row[14]), "active_injuries": injuries,
    }

@router.get("/{student_id}/muscle-fatigue")
def get_muscle_fatigue(student_id: int, user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT mg.muscle_name, mf.recovery_left, mf.recovery_hours, mf.status, mf.date
        FROM muscle_fatigue mf
        JOIN assigned_exercise_muscle_group aemg ON aemg.assigned_exercise_muscle_group_id = mf.assigned_exercise_muscle_group_id
        JOIN muscle_group mg ON mg.muscle_group_id = aemg.muscle_group_id
        WHERE mf.student_id = %s AND mf.status = 'ACTIVE'
        ORDER BY mf.recovery_left DESC
    """, (student_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return {
        "student_id": student_id,
        "active_fatigue": [{
            "muscle": r[0], "recovery_left_h": round(float(r[1]), 1),
            "recovery_total_h": round(float(r[2]), 1),
            "recovery_pct": round((1 - float(r[1])/float(r[2]))*100, 1),
            "since_date": str(r[4]),
        } for r in rows]
    }

# --- Teacher Endpoints ---
@router.put("/{student_id}/health-profile", tags=["Teacher"])
def update_health_profile(student_id: int, update: HealthProfileUpdate, user: dict = Depends(get_current_teacher)):
    conn = get_connection()
    cur = conn.cursor()
    updates, values = [], []
    for field, value in update.dict(exclude_none=True).items():
        updates.append(f"{field} = %s")
        values.append(value)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    values.append(student_id)
    cur.execute(f"UPDATE students_health_profiles SET {', '.join(updates)}, measurement_date = CURRENT_DATE WHERE student_id = %s RETURNING health_profile_id", values)
    row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Health profile not found")
    conn.commit(); cur.close(); conn.close()
    return {"updated": True, "profile_id": row[0]}

@router.post("/{student_id}/injuries", tags=["Teacher"])
def add_injury(student_id: int, injury: InjuryCreate, user: dict = Depends(get_current_teacher)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO student_injury_history (student_id, injury_type_id, diagnosis_date, recovery_date, recovery_status)
        VALUES (%s, %s, %s, %s, %s) RETURNING injury_record_id
    """, (student_id, injury.injury_type_id, injury.diagnosis_date, injury.recovery_date, injury.recovery_status))
    new_id = cur.fetchone()[0]
    conn.commit(); cur.close(); conn.close()
    return {"created": True, "injury_record_id": new_id}

@router.patch("/{student_id}/injuries/{injury_id}", tags=["Teacher"])
def update_injury(student_id: int, injury_id: int, update: InjuryUpdate, user: dict = Depends(get_current_teacher)):
    conn = get_connection()
    cur = conn.cursor()
    updates, values = [], []
    for field, value in update.dict(exclude_none=True).items():
        updates.append(f"{field} = %s")
        values.append(value)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    values.extend([injury_id, student_id])
    cur.execute(f"UPDATE student_injury_history SET {', '.join(updates)} WHERE injury_record_id = %s AND student_id = %s RETURNING injury_record_id", values)
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Injury not found")
    conn.commit(); cur.close(); conn.close()
    return {"updated": True}

@router.delete("/{student_id}/injuries/{injury_id}", tags=["Teacher"])
def delete_injury(student_id: int, injury_id: int, user: dict = Depends(get_current_teacher)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM student_injury_history WHERE injury_record_id = %s AND student_id = %s RETURNING injury_record_id", (injury_id, student_id))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Injury not found")
    conn.commit(); cur.close(); conn.close()
    return {"deleted": True}

@router.patch("/{student_id}/muscle-fatigue/{fatigue_id}", tags=["Teacher"])
def update_muscle_fatigue(student_id: int, fatigue_id: int, update: MuscleFatigueUpdate, user: dict = Depends(get_current_teacher)):
    conn = get_connection()
    cur = conn.cursor()
    updates, values = [], []
    for field, value in update.dict(exclude_none=True).items():
        updates.append(f"{field} = %s")
        values.append(value)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    values.extend([fatigue_id, student_id])
    cur.execute(f"UPDATE muscle_fatigue SET {', '.join(updates)} WHERE muscle_fatigue_id = %s AND student_id = %s RETURNING muscle_fatigue_id", values)
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="Fatigue record not found")
    conn.commit(); cur.close(); conn.close()
    return {"updated": True}