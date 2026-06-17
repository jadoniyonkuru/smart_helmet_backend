import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.helmet import HelmetCreate, HelmetUpdate, HelmetResponse
from app.schemas.sensor_data import SensorDataResponse, HelmetReadingCreate
from app.services.helmet_service import (
    get_all_helmets,
    get_helmet,
    create_helmet,
    update_helmet,
    delete_helmet,
)
from app.core.dependencies import get_current_active_user, require_admin
from app.models.sensor_data import SensorData
from app.models.user import User, UserRole
from app.models.supervisor import Supervisor

router = APIRouter()


@router.get("/", response_model=List[HelmetResponse])
async def list_helmets(
    skip: int = 0,
    limit: int = 100,
    assigned: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    supervisor_id = None
    if current_user.role == UserRole.supervisor:
        sup = (await db.execute(
            select(Supervisor).where(Supervisor.user_id == current_user.id)
        )).scalar_one_or_none()
        if sup:
            supervisor_id = sup.id
    return await get_all_helmets(db, skip, limit, assigned, supervisor_id)


@router.post("/", response_model=HelmetResponse, status_code=201)
async def add_helmet(
    data: HelmetCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_admin),
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
    _=Depends(require_admin),
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


@router.post(
    "/{helmet_id}/readings", response_model=SensorDataResponse, status_code=201
)
async def ingest_reading(
    helmet_id: uuid.UUID,
    data: HelmetReadingCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    from app.services.reading_processor import process_helmet_reading
    return await process_helmet_reading(db, helmet_id, data.model_dump())
