from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from datetime import date, timedelta, datetime
from feature_extractor import get_connection
from auth import get_current_user, get_current_student, get_current_teacher

router = APIRouter(prefix="/activity", tags=["Activity"])

class ActivityCreate(BaseModel):
    date: date
    active_minutes: int
    steps: int
    calories: Optional[float] = None
    notes: Optional[str] = None

def ensure_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL,
            date DATE NOT NULL,
            active_minutes INTEGER NOT NULL DEFAULT 0,
            steps INTEGER NOT NULL DEFAULT 0,
            calories FLOAT,
            notes TEXT,
            UNIQUE(student_id, date)
        )
    """)
    conn.commit()
    cur.close(); conn.close()

@router.get("/{student_id}")
def get_activity(student_id: int, days: int = Query(7, ge=1, le=365), user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    ensure_tables()
    conn = get_connection()
    cur = conn.cursor()
    since = (datetime.now() - timedelta(days=days)).date()
    cur.execute("""
        SELECT date, active_minutes, steps, calories
        FROM activity_log
        WHERE student_id = %s AND date >= %s
        ORDER BY date ASC
    """, (student_id, since))
    rows = cur.fetchall()
    cur.close(); conn.close()
    if not rows:
        return []
    return [{"date": str(r[0]), "active_minutes": r[1], "steps": r[2]} for r in rows]

@router.post("/{student_id}")
def upsert_activity(student_id: int, activity: ActivityCreate, user: dict = Depends(get_current_student)):
    if user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    ensure_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO activity_log (student_id, date, active_minutes, steps, calories, notes)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (student_id, date)
        DO UPDATE SET active_minutes = EXCLUDED.active_minutes,
                      steps = EXCLUDED.steps,
                      calories = EXCLUDED.calories,
                      notes = EXCLUDED.notes
        RETURNING id
    """, (student_id, activity.date, activity.active_minutes, activity.steps, activity.calories, activity.notes))
    row_id = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()
    return {"recorded": True, "id": row_id}
