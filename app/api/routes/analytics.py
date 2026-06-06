from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.models.alert import Alert, AlertType
from app.models.helmet import Helmet
from app.models.worker import Worker
from app.models.gateway import Gateway
from app.models.sensor_data import SensorData

router = APIRouter()


@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_db), _=Depends(get_current_active_user)):
    total_helmets = (await db.execute(select(func.count()).select_from(Helmet))).scalar()
    total_workers = (
        await db.execute(select(func.count()).select_from(Worker).where(Worker.is_active == True))
    ).scalar()
    unresolved_alerts = (
        await db.execute(select(func.count()).select_from(Alert).where(Alert.is_resolved == False))
    ).scalar()
    return {
        "total_helmets": total_helmets,
        "total_workers": total_workers,
        "unresolved_alerts": unresolved_alerts,
    }


@router.get("/alert-trends")
async def alert_trends(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(func.date(Alert.created_at).label("date"), func.count(Alert.id).label("count"))
        .where(Alert.created_at >= since)
        .group_by(func.date(Alert.created_at))
        .order_by(func.date(Alert.created_at))
    )
    return [{"date": str(r[0]), "count": r[1]} for r in result.all()]


@router.get("/alerts-by-type")
async def alerts_by_type(db: AsyncSession = Depends(get_db), _=Depends(get_current_active_user)):
    result = await db.execute(select(Alert.type, func.count(Alert.id)).group_by(Alert.type))
    return [{"type": r[0], "count": r[1]} for r in result.all()]


@router.get("/alerts-by-level")
async def alerts_by_level(db: AsyncSession = Depends(get_db), _=Depends(get_current_active_user)):
    result = await db.execute(select(Alert.level, func.count(Alert.id)).group_by(Alert.level))
    return [{"level": r[0], "count": r[1]} for r in result.all()]


@router.get("/gas-levels")
async def gas_levels(db: AsyncSession = Depends(get_db), _=Depends(get_current_active_user)):
    result = await db.execute(
        select(
            func.avg(SensorData.gas_level),
            func.max(SensorData.gas_level),
            func.min(SensorData.gas_level),
            func.avg(SensorData.co_ppm),
            func.max(SensorData.co_ppm),
        )
    )
    r = result.one()
    return {
        "avg_gas_level": r[0],
        "max_gas_level": r[1],
        "min_gas_level": r[2],
        "avg_co_ppm": r[3],
        "max_co_ppm": r[4],
    }


@router.get("/compliance")
async def compliance(db: AsyncSession = Depends(get_db), _=Depends(get_current_active_user)):
    total = (await db.execute(select(func.count()).select_from(SensorData))).scalar()
    worn = (
        await db.execute(
            select(func.count()).select_from(SensorData).where(SensorData.helmet_worn == True)
        )
    ).scalar()
    rate = round((worn / total * 100), 2) if total > 0 else 0.0
    return {"total_readings": total, "helmet_worn": worn, "compliance_rate_pct": rate}


@router.get("/impacts")
async def impacts(db: AsyncSession = Depends(get_db), _=Depends(get_current_active_user)):
    vibrations = (
        await db.execute(
            select(func.count()).select_from(SensorData).where(SensorData.vibration_detected == True)
        )
    ).scalar()
    fall_alerts = (
        await db.execute(
            select(func.count()).select_from(Alert).where(Alert.type == AlertType.fall)
        )
    ).scalar()
    return {"total_vibration_events": vibrations, "fall_alerts": fall_alerts}


@router.get("/environment")
async def environment(db: AsyncSession = Depends(get_db), _=Depends(get_current_active_user)):
    result = await db.execute(
        select(
            func.avg(SensorData.temperature), func.max(SensorData.temperature), func.min(SensorData.temperature),
            func.avg(SensorData.humidity),    func.max(SensorData.humidity),    func.min(SensorData.humidity),
        )
    )
    r = result.one()
    return {
        "temperature": {"avg": r[0], "max": r[1], "min": r[2]},
        "humidity":    {"avg": r[3], "max": r[4], "min": r[5]},
    }


@router.get("/network-health")
async def network_health(db: AsyncSession = Depends(get_db), _=Depends(get_current_active_user)):
    total = (await db.execute(select(func.count()).select_from(Gateway))).scalar()
    online = (
        await db.execute(select(func.count()).select_from(Gateway).where(Gateway.is_online == True))
    ).scalar()
    avg_pdr = (await db.execute(select(func.avg(Gateway.packet_delivery_rate)))).scalar()
    return {
        "total_gateways": total,
        "online": online,
        "offline": total - online,
        "avg_packet_delivery_rate": round(avg_pdr or 0.0, 2),
    }
