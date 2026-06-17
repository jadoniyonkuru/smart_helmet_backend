import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.api.routes import (
    auth,
    helmets,
    workers,
    supervisors,
    alerts,
    analytics,
    reports,
    system,
    ws,
    notifications,
    departments,
)
from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _seed_admin() -> None:
    async with _Session() as db:
        result = await db.execute(
            select(User).where(User.email == settings.FIRST_ADMIN_EMAIL)
        )
        if result.scalar_one_or_none():
            return
        admin = User(
            email=settings.FIRST_ADMIN_EMAIL,
            full_name="System Admin",
            hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
            role=UserRole.admin,
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        await db.commit()
        logger.info("Admin user created: %s", settings.FIRST_ADMIN_EMAIL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _seed_admin()

    # AI models
    try:
        from app.services.ai_service import ai_service
        if getattr(ai_service, "models_loaded", False):
            logger.info("[STARTUP] AI models loaded — inference active")
        else:
            logger.warning(
                "[STARTUP] AI models NOT loaded — inference disabled"
            )
    except Exception:
        logger.warning(
            "[STARTUP] AI service unavailable (ML dependencies may be missing)"
        )

    # MQTT — subscribe to helmet readings and start broker connection
    from app.services.mqtt_service import mqtt_service
    from app.mqtt.handlers import on_helmet_reading
    try:
        mqtt_service.subscribe("safehelm/helmets/+/readings", on_helmet_reading)
        mqtt_service.start(asyncio.get_running_loop())
    except Exception as exc:
        logger.error("[STARTUP] MQTT service failed to start: %s", exc)

    yield

    # Shutdown MQTT cleanly
    try:
        mqtt_service.stop()
    except Exception:
        pass


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=True,
)

Path("uploads/avatars").mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://smart-safety-helmet.vercel.app",
        settings.FRONTEND_URL,
    ],
    # allow_origins only matches exact strings, so the previous
    # "https://*.vercel.app" / "https://*.railway.app" entries never
    # actually matched anything — use a regex to cover preview deployments.
    allow_origin_regex=r"https://.*\.(vercel|railway)\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(helmets.router, prefix="/api/v1/helmets", tags=["helmets"])
app.include_router(workers.router, prefix="/api/v1/workers", tags=["workers"])
app.include_router(
    supervisors.router,
    prefix="/api/v1/supervisors",
    tags=["supervisors"],
)
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])
app.include_router(
    analytics.router,
    prefix="/api/v1/analytics",
    tags=["analytics"],
)
app.include_router(reports.router, prefix="/api/v1/reports", tags=["reports"])
app.include_router(system.router, prefix="/api/v1/system", tags=["system"])
app.include_router(ws.router, prefix="/ws", tags=["websockets"])
app.include_router(
    notifications.router,
    prefix="/api/v1/notifications",
    tags=["notifications"],
)
app.include_router(
    departments.router, prefix="/api/v1/departments", tags=["departments"]
)


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
