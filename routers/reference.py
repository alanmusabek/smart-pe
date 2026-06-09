from fastapi import APIRouter
from feature_extractor import get_connection

router = APIRouter(tags=["Reference"])

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