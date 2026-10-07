from fastapi import APIRouter, Depends
from auth import get_current_teacher
from feature_extractor import get_connection

router = APIRouter(tags=["Reference"])

@router.get('/injury-types')
def injury_types(user: dict = Depends(get_current_teacher)):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT injury_type_id, type_name, body_region FROM injury_types ORDER BY type_name')
            return [{'id': r[0], 'name': r[1], 'region': r[2]} for r in cur.fetchall()]
    finally:
        conn.close()

@router.get("/exercises")
def get_all_exercises():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT exercise_id, exercise_name, category_id, difficulty, recommended_sets, recommended_reps
        FROM exercises
        ORDER BY category_id, exercise_name
    """)
    rows = cur.fetchall()
    cur.close(); conn.close()
    return {
        "exercises": [{
            "exercise_id": r[0], "exercise_name": r[1], "category_id": r[2],
            "difficulty": r[3], "recommended_sets": r[4], "recommended_reps": r[5]
        } for r in rows]
    }
