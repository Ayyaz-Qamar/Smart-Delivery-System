"""
FastAPI entry point for the Smart Delivery Route Optimization System.

Run locally with:
    uvicorn main:app --reload --port 8000
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine
from routers import auth_router, delivery_router, ml_router, tracking_router

# Create all tables on startup. In production, use Alembic migrations instead.
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Smart Delivery Route Optimization API",
    description="ML-powered route optimization, ETA prediction, and live tracking.",
    version="1.0.0",
)

# CORS — allow the React frontend in dev. Lock this down in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(delivery_router.router)
app.include_router(ml_router.router)
app.include_router(tracking_router.router)


@app.get("/")
def root():
    return {
        "name": "Smart Delivery Route Optimization API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
