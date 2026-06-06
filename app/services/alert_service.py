import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.models.alert import Alert
from app.schemas.alert import AlertCreate, AlertResolve


async def get_alerts(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(
        select(Alert).order_by(Alert.created_at.desc()).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def get_unresolved_alerts(db: AsyncSession):
    result = await db.execute(
        select(Alert).where(Alert.is_resolved == False).order_by(Alert.created_at.desc())
    )
    return result.scalars().all()


async def create_alert(db: AsyncSession, data: AlertCreate) -> Alert:
    alert = Alert(**data.model_dump())
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return alert


async def resolve_alert(db: AsyncSession, alert_id: uuid.UUID, data: AlertResolve) -> Alert:
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_resolved = True
    alert.resolved_at = datetime.utcnow()
    alert.resolved_by = data.resolved_by
    await db.commit()
    await db.refresh(alert)
    return alert
