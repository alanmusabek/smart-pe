from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from feature_extractor import get_connection
from auth import get_current_user, get_current_student, get_current_teacher

router = APIRouter(prefix="/attendance", tags=["Attendance"])

class CheckInRequest(BaseModel):
    qr_code: str

def ensure_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS qr_sessions (
            id SERIAL PRIMARY KEY,
            qr_code VARCHAR(255) UNIQUE NOT NULL,
            session_date DATE NOT NULL DEFAULT CURRENT_DATE,
            created_by INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS attendance_records (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL,
            qr_session_id INTEGER NOT NULL REFERENCES qr_sessions(id),
            check_in_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close(); conn.close()

@router.post("/checkin")
def checkin(req: CheckInRequest, user: dict = Depends(get_current_student)):
    ensure_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, qr_code, session_date, created_by FROM qr_sessions WHERE qr_code = %s", (req.qr_code,))
    session = cur.fetchone()
    if not session:
        cur.close(); conn.close()
        raise HTTPException(status_code=404, detail="QR session not found")
    session_id = session[0]
    cur.execute(
        "INSERT INTO attendance_records (student_id, qr_session_id) VALUES (%s, %s) RETURNING id",
        (user["student_id"], session_id)
    )
    record_id = cur.fetchone()[0]
    conn.commit()
    cur.close(); conn.close()
    return {
        "recorded": True,
        "session": {
            "id": session[0], "qr_code": session[1],
            "session_date": str(session[2]), "created_by": session[3],
        }
    }

@router.get("/{student_id}/journal")
def get_attendance_journal(student_id: int, user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT ar.id, ar.student_id, ar.check_in_time,
               qs.id, qs.qr_code, qs.session_date
        FROM attendance_records ar
        JOIN qr_sessions qs ON qs.id = ar.qr_session_id
        WHERE ar.student_id = %s
        ORDER BY ar.check_in_time DESC
    """, (student_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{
        "record_id": r[0], "student_id": r[1], "check_in_time": str(r[2]),
        "session": {"id": r[3], "qr_code": r[4], "session_date": str(r[5])},
    } for r in rows]

@router.get("/sessions")
def get_available_sessions(user: dict = Depends(get_current_student)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, qr_code, session_date, created_by FROM qr_sessions ORDER BY session_date DESC")
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{"id": r[0], "qr_code": r[1], "session_date": str(r[2]), "created_by": r[3]} for r in rows]
