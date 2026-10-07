import os
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from auth import get_current_teacher
from schemas import RetrainRequest
from core.settings import settings

router = APIRouter(prefix="/model", tags=["Model"])
MODEL_PATH = "fitness_ranker.pkl"

@router.get("/status")
def model_status(user: dict = Depends(get_current_teacher)):
    from retrain import check_readiness, retrain_history
    exists = os.path.exists(MODEL_PATH)
    ready = check_readiness() if exists else {"ready": False}
    history = retrain_history()
    last = history[-1] if history else None
    return {
        "model_loaded": exists, "model_path": MODEL_PATH,
        "retrain_ready": ready.get("ready", False),
        "retrain_enabled": settings.MODEL_RETRAIN_ENABLED,
        "new_interactions": ready.get("new_interactions", 0),
        "threshold": ready.get("threshold", 200),
        "last_retrain": last,
        "total_retrains": len([e for e in history if e.get("status") == "replaced"]),
    }

@router.post("/retrain")
def trigger_retrain(request: RetrainRequest, background_tasks: BackgroundTasks, user: dict = Depends(get_current_teacher)):
    if not settings.MODEL_RETRAIN_ENABLED:
        raise HTTPException(status_code=403, detail="Retraining is disabled on this demonstration server. Existing model predictions remain available.")
    from retrain import run_retrain, check_readiness
    if not request.force:
        readiness = check_readiness()
        if not readiness["ready"]:
            return {"started": False, "reason": f"Not enough new data ({readiness['new_interactions']} / {readiness['threshold']}). Use force=true to override."}
    background_tasks.add_task(run_retrain, force=request.force)
    return {"started": True, "message": "Retraining started in background.", "forced": request.force}

@router.get("/retrain/history")
def get_retrain_history(user: dict = Depends(get_current_teacher)):
    from retrain import retrain_history
    return {"history": retrain_history()}
