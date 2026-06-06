import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.helmet import HelmetCreate, HelmetUpdate, HelmetResponse
from app.schemas.sensor_data import SensorDataResponse
from app.services.helmet_service import get_all_helmets, get_helmet, create_helmet, update_helmet, delete_helmet
from app.core.dependencies import get_current_active_user
from app.models.sensor_data import SensorData

router = APIRouter()


@router.get("/", response_model=List[HelmetResponse])
async def list_helmets(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return await get_all_helmets(db, skip, limit)


@router.post("/", response_model=HelmetResponse, status_code=201)
async def add_helmet(
    data: HelmetCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return await create_helmet(db, data)


@router.get("/{helmet_id}", response_model=HelmetResponse)
async def read_helmet(
    helmet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return await get_helmet(db, helmet_id)


@router.patch("/{helmet_id}", response_model=HelmetResponse)
async def edit_helmet(
    helmet_id: uuid.UUID,
    data: HelmetUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    return await update_helmet(db, helmet_id, data)


@router.delete("/{helmet_id}", status_code=204)
async def remove_helmet(
    helmet_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    await delete_helmet(db, helmet_id)


@router.get("/{helmet_id}/sensor-data", response_model=List[SensorDataResponse])
async def helmet_sensor_data(
    helmet_id: uuid.UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    result = await db.execute(
        select(SensorData)
        .where(SensorData.helmet_id == helmet_id)
        .order_by(SensorData.recorded_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
