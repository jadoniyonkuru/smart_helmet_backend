import psutil
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.core.config import settings
from app.models.system_health import SystemHealthLog

router = APIRouter()

_runtime_settings: dict = {}


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/db-health")
async def db_health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}


@router.get("/performance")
async def performance(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    mem  = psutil.virtual_memory()
    disk = psutil.disk_usage(".")
    cpu  = psutil.cpu_percent(interval=0.1)

    db.add(SystemHealthLog(
        cpu_percent=cpu,
        memory_percent=mem.percent,
        disk_percent=disk.percent,
    ))
    await db.commit()

    return {
        "cpu_percent": cpu,
        "memory": {
            "total_mb": round(mem.total / 1024 / 1024, 1),
            "used_mb":  round(mem.used  / 1024 / 1024, 1),
            "percent":  mem.percent,
        },
        "disk": {
            "total_gb": round(disk.total / 1024 / 1024 / 1024, 1),
            "used_gb":  round(disk.used  / 1024 / 1024 / 1024, 1),
            "percent":  disk.percent,
        },
    }


@router.get("/settings")
async def get_settings(_=Depends(get_current_active_user)):
    return {
        "app_name": settings.APP_NAME,
        "debug": settings.DEBUG,
        "algorithm": settings.ALGORITHM,
        "access_token_expire_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        "mqtt_broker_host": settings.MQTT_BROKER_HOST,
        "mqtt_broker_port": settings.MQTT_BROKER_PORT,
        **_runtime_settings,
    }


@router.put("/settings")
async def update_settings(data: dict, _=Depends(get_current_active_user)):
    allowed = {"access_token_expire_minutes", "debug"}
    filtered = {k: v for k, v in data.items() if k in allowed}
    _runtime_settings.update(filtered)
    return {"message": "Settings updated", "updated": filtered}
