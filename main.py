"""
main.py — FastAPI backend for Smart PE recommendation system
Run: uvicorn main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
from chatbot.sessions import invalidate
from auth import router as auth_router
from routers import students, plans, interactions, model, explain, reference, chatbot, attendance, activity, achievements

@asynccontextmanager
async def lifespan(app):
    from core.settings import settings
    if settings.DEMO_MODE:
        from deployment.bootstrap_demo import bootstrap_demo
        bootstrap_demo(settings.DB_URL, settings.DEMO_TEACHER_PASSWORD, settings.DEMO_STUDENT_PASSWORD)
    # Load the ranking model serially before request threads can import XGBoost.
    # Concurrent first imports through joblib and SHAP caused partial modules.
    if os.path.exists("fitness_ranker.pkl"):
        from core.model_cache import load_model
        load_model()
    yield

app = FastAPI(
    title="Smart PE — Workout Recommendation API",
    description="AI-powered physical education workout planner",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Include routers
app.include_router(auth_router)
app.include_router(students.router)
app.include_router(plans.router)
app.include_router(interactions.router)
app.include_router(model.router)
app.include_router(explain.router)
app.include_router(reference.router)
app.include_router(chatbot.router)
app.include_router(attendance.router)
app.include_router(activity.router)
app.include_router(achievements.router)

MODEL_PATH = "fitness_ranker.pkl"

@app.middleware('http')
async def refresh_chat_after_write(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/app/assets/') and response.status_code == 200:
        response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif request.url.path in ('/app/', '/app/index.html'):
        response.headers['Cache-Control'] = 'no-cache'
    if (request.method in {'POST', 'PUT', 'PATCH', 'DELETE'}
            and response.status_code < 400
            and request.url.path.startswith(('/students', '/plans', '/interactions', '/activity'))):
        invalidate()
    return response

frontend_dist = Path(__file__).parent / 'frontend' / 'dist'
if frontend_dist.is_dir():
    app.mount('/app', StaticFiles(directory=frontend_dist, html=True), name='frontend')

@app.get("/health", tags=["Health"])
def root():
    return {
        "service": "Smart PE Recommendation API",
        "version": "1.0.0",
        "model_ready": os.path.exists(MODEL_PATH),
        "docs": "/docs",
    }

@app.get('/', include_in_schema=False)
def frontend():
    if frontend_dist.is_dir():
        return RedirectResponse('/app/')
    return {'message': 'Build the React frontend: cd frontend && npm ci && npm run build', 'docs': '/docs'}
