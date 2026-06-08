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
from app.models.user import User, UserRole
from app.models.system_health import SystemHealthLog

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

    co_safe = (await db.execute(
        select(func.count()).select_from(SensorData)
        .where(SensorData.co_ppm.isnot(None), SensorData.co_ppm < 50)
    )).scalar()
    co_warning = (await db.execute(
        select(func.count()).select_from(SensorData)
        .where(SensorData.co_ppm >= 50, SensorData.co_ppm < 200)
    )).scalar()
    co_critical = (await db.execute(
        select(func.count()).select_from(SensorData)
        .where(SensorData.co_ppm.isnot(None), SensorData.co_ppm >= 200)
    )).scalar()

    ch4_safe = (await db.execute(
        select(func.count()).select_from(SensorData)
        .where(SensorData.ch4_percent.isnot(None), SensorData.ch4_percent < 1.0)
    )).scalar()
    ch4_warning = (await db.execute(
        select(func.count()).select_from(SensorData)
        .where(SensorData.ch4_percent >= 1.0, SensorData.ch4_percent < 2.0)
    )).scalar()
    ch4_critical = (await db.execute(
        select(func.count()).select_from(SensorData)
        .where(SensorData.ch4_percent.isnot(None), SensorData.ch4_percent >= 2.0)
    )).scalar()

    return {
        "avg_gas_level": r[0],
        "max_gas_level": r[1],
        "min_gas_level": r[2],
        "avg_co_ppm": r[3],
        "max_co_ppm": r[4],
        "co_distribution": {
            "safe": co_safe,
            "warning": co_warning,
            "critical": co_critical,
        },
        "ch4_distribution": {
            "safe": ch4_safe,
            "warning": ch4_warning,
            "critical": ch4_critical,
        },
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


@router.get("/active-sessions")
async def active_sessions(db: AsyncSession = Depends(get_db), _=Depends(get_current_active_user)):
    total_supervisors = (await db.execute(
        select(func.count()).select_from(User)
        .where(User.role == UserRole.supervisor, User.is_active == True)
    )).scalar()
    total_admins = (await db.execute(
        select(func.count()).select_from(User)
        .where(User.role == UserRole.admin, User.is_active == True)
    )).scalar()
    return {
        "active_supervisors": total_supervisors,
        "active_admins": total_admins,
        "total_active_users": total_supervisors + total_admins,
    }


@router.get("/usage-trends")
async def usage_trends(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    since = datetime.utcnow() - timedelta(days=days)

    helmets_result = await db.execute(
        select(func.date(Helmet.created_at).label("date"), func.count(Helmet.id).label("count"))
        .where(Helmet.created_at >= since)
        .group_by(func.date(Helmet.created_at))
        .order_by(func.date(Helmet.created_at))
    )
    workers_result = await db.execute(
        select(func.date(Worker.created_at).label("date"), func.count(Worker.id).label("count"))
        .where(Worker.created_at >= since)
        .group_by(func.date(Worker.created_at))
        .order_by(func.date(Worker.created_at))
    )
    gateways_result = await db.execute(
        select(func.date(Gateway.created_at).label("date"), func.count(Gateway.id).label("count"))
        .where(Gateway.created_at >= since)
        .group_by(func.date(Gateway.created_at))
        .order_by(func.date(Gateway.created_at))
    )

    return {
        "days": days,
        "helmets":  [{"date": str(r[0]), "count": r[1]} for r in helmets_result.all()],
        "workers":  [{"date": str(r[0]), "count": r[1]} for r in workers_result.all()],
        "gateways": [{"date": str(r[0]), "count": r[1]} for r in gateways_result.all()],
    }


@router.get("/department-distribution")
async def department_distribution(db: AsyncSession = Depends(get_db), _=Depends(get_current_active_user)):
    result = await db.execute(
        select(Worker.zone, func.count(Worker.id).label("count"))
        .where(Worker.zone.isnot(None))
        .group_by(Worker.zone)
        .order_by(func.count(Worker.id).desc())
    )
    rows = result.all()
    total = sum(r[1] for r in rows)
    return [
        {
            "zone": r[0],
            "count": r[1],
            "percentage": round(r[1] / total * 100, 1) if total > 0 else 0.0,
        }
        for r in rows
    ]


@router.get("/system-health-trends")
async def system_health_trends(
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    since = datetime.utcnow() - timedelta(hours=hours)
    result = await db.execute(
        select(SystemHealthLog)
        .where(SystemHealthLog.recorded_at >= since)
        .order_by(SystemHealthLog.recorded_at.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "timestamp": r.recorded_at.isoformat(),
            "cpu":    round(r.cpu_percent, 1),
            "memory": round(r.memory_percent, 1),
            "disk":   round(r.disk_percent, 1),
        }
        for r in rows
    ]


@router.get("/peak-hours")
async def peak_hours(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(
            func.extract("hour", Alert.created_at).label("hour"),
            func.count(Alert.id).label("count"),
        )
        .where(Alert.created_at >= since)
        .group_by(func.extract("hour", Alert.created_at))
        .order_by(func.extract("hour", Alert.created_at))
    )
    counts = {int(r[0]): r[1] for r in result.all()}
    return [{"hour": h, "label": f"{h:02d}:00", "alert_count": counts.get(h, 0)} for h in range(24)]
