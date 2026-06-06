import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.alert import AlertCreate, AlertResolve, AlertResponse
from app.services.alert_service import get_alerts, get_unresolved_alerts, create_alert, resolve_alert
from app.core.dependencies import get_current_active_user
from app.models.alert import Alert

router = APIRouter()


@router.get("/", response_model=List[AlertResponse])
async def list_alerts(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return await get_alerts(db, skip, limit)


@router.get("/unresolved", response_model=List[AlertResponse])
async def unresolved_alerts(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return await get_unresolved_alerts(db)


@router.get("/feed", response_model=List[AlertResponse])
async def alerts_feed(
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(
        select(Alert).order_by(Alert.created_at.desc()).limit(20)
    )
    return result.scalars().all()


@router.post("/", response_model=AlertResponse, status_code=201)
async def add_alert(
    data: AlertCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return await create_alert(db, data)


@router.patch("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve(
    alert_id: uuid.UUID,
    data: AlertResolve,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return await resolve_alert(db, alert_id, data)


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(alert)
    await db.commit()
