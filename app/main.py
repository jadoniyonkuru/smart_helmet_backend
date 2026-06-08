from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.routes import (
    auth, helmets, workers, supervisors, gateways,
    alerts, analytics, reports, system, ws, notifications,
)
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)

Path("uploads/avatars").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,        prefix="/api/v1/auth",        tags=["auth"])
app.include_router(helmets.router,     prefix="/api/v1/helmets",     tags=["helmets"])
app.include_router(workers.router,     prefix="/api/v1/workers",     tags=["workers"])
app.include_router(supervisors.router, prefix="/api/v1/supervisors", tags=["supervisors"])
app.include_router(gateways.router,    prefix="/api/v1/gateways",    tags=["gateways"])
app.include_router(alerts.router,      prefix="/api/v1/alerts",      tags=["alerts"])
app.include_router(analytics.router,   prefix="/api/v1/analytics",   tags=["analytics"])
app.include_router(reports.router,     prefix="/api/v1/reports",     tags=["reports"])
app.include_router(system.router,      prefix="/api/v1/system",      tags=["system"])
app.include_router(ws.router,           prefix="/ws",                          tags=["websockets"])
app.include_router(notifications.router, prefix="/api/v1/notifications",       tags=["notifications"])


@app.get("/", tags=["root"])
async def root():
    return {
        "project": "Smart_Helmet API",
        "version": "1.0.0",
        "status": "running",
        "docs": "http://127.0.0.1:8000/docs",
        "redoc": "http://127.0.0.1:8000/redoc",
        "api_base": "http://127.0.0.1:8000/api/v1",
    }
