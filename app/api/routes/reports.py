import csv
import io
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.models.alert import Alert, AlertLevel
from app.models.sensor_data import SensorData

router = APIRouter()


class ReportRequest(BaseModel):
    title: str
    start: datetime
    end: datetime
    include_alerts: bool = True
    include_sensor_summary: bool = False
    helmet_ids: Optional[List[uuid.UUID]] = None


@router.get("/alerts")
async def alert_report(
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(
        select(Alert).where(Alert.created_at >= start, Alert.created_at <= end)
    )
    alerts = result.scalars().all()
    return {"total": len(alerts), "alerts": alerts}


@router.get("/sensor-data/{helmet_id}")
async def sensor_data_report(
    helmet_id: uuid.UUID,
    start: datetime = Query(...),
    end: datetime = Query(...),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(
        select(SensorData).where(
            SensorData.helmet_id == helmet_id,
            SensorData.recorded_at >= start,
            SensorData.recorded_at <= end,
        )
    )
    data = result.scalars().all()
    return {"helmet_id": str(helmet_id), "total": len(data), "data": data}


@router.post("/generate")
async def generate_report(
    data: ReportRequest,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    report = {
        "title": data.title,
        "generated_at": datetime.utcnow().isoformat(),
        "period": {"start": data.start.isoformat(), "end": data.end.isoformat()},
    }
    if data.include_alerts:
        alerts = (
            await db.execute(
                select(Alert).where(Alert.created_at >= data.start, Alert.created_at <= data.end)
            )
        ).scalars().all()
        report["alerts"] = {
            "total": len(alerts),
            "critical": sum(1 for a in alerts if a.level == AlertLevel.critical),
            "resolved": sum(1 for a in alerts if a.is_resolved),
        }
    if data.include_sensor_summary:
        q = select(SensorData).where(
            SensorData.recorded_at >= data.start, SensorData.recorded_at <= data.end
        )
        if data.helmet_ids:
            q = q.where(SensorData.helmet_id.in_(data.helmet_ids))
        readings = (await db.execute(q)).scalars().all()
        report["sensor_data"] = {"total_readings": len(readings)}
    return report


@router.get("/export")
async def export_report(
    resource: str = Query("alerts", enum=["alerts", "sensor_data"]),
    format: str = Query("json", enum=["json", "csv"]),
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    if resource == "alerts":
        items = (
            await db.execute(select(Alert).order_by(Alert.created_at.desc()).limit(1000))
        ).scalars().all()
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["id", "type", "level", "message", "is_resolved", "helmet_id", "worker_id", "created_at"])
            for a in items:
                writer.writerow([str(a.id), a.type, a.level, a.message, a.is_resolved,
                                  str(a.helmet_id), str(a.worker_id), a.created_at])
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=alerts.csv"},
            )
        return {"resource": resource, "total": len(items), "data": items}

    items = (
        await db.execute(select(SensorData).order_by(SensorData.recorded_at.desc()).limit(1000))
    ).scalars().all()
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "helmet_id", "temperature", "humidity", "gas_level",
                          "co_ppm", "vibration_detected", "helmet_worn", "recorded_at"])
        for d in items:
            writer.writerow([str(d.id), str(d.helmet_id), d.temperature, d.humidity,
                              d.gas_level, d.co_ppm, d.vibration_detected, d.helmet_worn, d.recorded_at])
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=sensor_data.csv"},
        )
    return {"resource": resource, "total": len(items), "data": items}


@router.get("/audit-logs")
async def audit_logs(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(
        select(Alert).order_by(Alert.created_at.desc()).offset(skip).limit(limit)
    )
    alerts = result.scalars().all()
    return {
        "total": len(alerts),
        "logs": [
            {
                "id": str(a.id),
                "event": f"Alert triggered: {a.type} [{a.level}]",
                "detail": a.message,
                "status": "resolved" if a.is_resolved else "active",
                "timestamp": a.created_at.isoformat(),
            }
            for a in alerts
        ],
    }
