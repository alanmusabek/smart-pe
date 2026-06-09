import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from plan_assembler import generate_plan
from explainability import explain_exercise, explain_exercise_ru, explain_plan_ru, explain_plan_shap, FEATURE_LABELS_RU
from auth import get_current_user

router = APIRouter(prefix="/explain", tags=["Explainability"])
MODEL_PATH = "fitness_ranker.pkl"

@router.get("/exercise/{student_id}/{exercise_id}")
def explain_exercise_endpoint(student_id: int, exercise_id: int, user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=503, detail="Model not found")
    try:
        result = explain_exercise(student_id, exercise_id)
        result["shap_values_labeled"] = {FEATURE_LABELS_RU.get(f, f): v for f, v in result["shap_values"].items()}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/exercise/{student_id}/{exercise_id}/ru")
def explain_exercise_ru_endpoint(student_id: int, exercise_id: int, user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=503, detail="Model not found")
    try:
        text = explain_exercise_ru(student_id, exercise_id)
        return {"student_id": student_id, "exercise_id": exercise_id, "explanation": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plan/{student_id}/ru")
def explain_plan_ru_endpoint(student_id: int, user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=503, detail="Model not found")
    try:
        weekly_plan = generate_plan(student_id, save_to_db=False)
        explanation = explain_plan_ru(student_id, weekly_plan)
        return {"student_id": student_id, "plan": weekly_plan, "explanation": explanation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/plan/{student_id}/shap-plot")
def explain_plan_shap_plot(student_id: int, user: dict = Depends(get_current_user)):
    if user["role"] == "student" and user["student_id"] != student_id:
        raise HTTPException(status_code=403, detail="Access denied")
    if not os.path.exists(MODEL_PATH):
        raise HTTPException(status_code=503, detail="Model not found")
    try:
        plot_path = f"shap_plan_{student_id}.png"
        weekly_plan = generate_plan(student_id, save_to_db=False)
        explain_plan_shap(student_id, weekly_plan, plot_path=plot_path)
        return FileResponse(plot_path, media_type="image/png", filename=f"shap_plan_student_{student_id}.png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))