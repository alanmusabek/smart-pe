from fastapi import APIRouter, HTTPException, Depends
from feature_extractor import get_connection
from auth import get_current_user, get_current_student, get_current_teacher

router = APIRouter(prefix="/achievements", tags=["Achievements"])

def ensure_tables():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id SERIAL PRIMARY KEY,
            student_id INTEGER NOT NULL,
            achievement_type VARCHAR(100) NOT NULL,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            unlocked_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close(); conn.close()

@router.get("/{student_id}")
def get_achievements(student_id: int, user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    ensure_tables()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, achievement_type, title, description, unlocked_at
        FROM achievements
        WHERE student_id = %s
        ORDER BY unlocked_at DESC
    """, (student_id,))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return [{
        "id": r[0], "achievement_type": r[1], "title": r[2],
        "description": r[3], "unlocked_at": str(r[4]),
    } for r in rows]
