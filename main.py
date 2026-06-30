"""
main.py — FastAPI backend for Smart PE recommendation system
Run: uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
import os
from fastapi import FastAPI
from auth import router as auth_router
from routers import students, plans, interactions, model, explain, reference, chatbot, classes, analytics

app = FastAPI(
    title="Smart PE — Workout Recommendation API",
    description="AI-powered physical education workout planner",
    version="1.0.0",
)

# Include routers
app.include_router(auth_router)
app.include_router(students.router)
app.include_router(plans.router)
app.include_router(interactions.router)
app.include_router(model.router)
app.include_router(explain.router)
app.include_router(reference.router)
app.include_router(chatbot.router)
app.include_router(classes.router)
app.include_router(analytics.router)

MODEL_PATH = "fitness_ranker.pkl"

@app.get("/", tags=["Health"])
def root():
    return {
        "service": "Smart PE Recommendation API",
        "version": "1.0.0",
        "model_ready": os.path.exists(MODEL_PATH),
        "docs": "/docs",
    }
