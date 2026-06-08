import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.schemas.helmet import HelmetCreate, HelmetUpdate, HelmetResponse
from app.schemas.sensor_data import SensorDataResponse, HelmetReadingCreate
from app.services.helmet_service import get_all_helmets, get_helmet, create_helmet, update_helmet, delete_helmet
from app.core.dependencies import get_current_active_user
from app.models.sensor_data import SensorData
from app.models.alert import Alert, AlertLevel, AlertType
from app.models.helmet import HelmetStatus

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


@router.post("/{helmet_id}/readings", response_model=SensorDataResponse, status_code=201)
async def ingest_reading(
    helmet_id: uuid.UUID,
    data: HelmetReadingCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(get_current_active_user),
):
    helmet = await get_helmet(db, helmet_id)

    reading = SensorData(
        helmet_id=helmet_id,
        co_ppm=data.co,
        ch4_percent=data.ch4,
        temperature=data.temperature,
        humidity=data.humidity,
        helmet_worn=data.helmetWear if data.helmetWear is not None else True,
        vibration_detected=data.impactDetected if data.impactDetected is not None else False,
        battery_level=data.battery,
        signal_strength=data.signalStrength,
        accelerometer_x=data.accelerometerX,
        accelerometer_y=data.accelerometerY,
        accelerometer_z=data.accelerometerZ,
        gas_level=data.gasLevel,
    )
    db.add(reading)

    helmet.last_seen = datetime.utcnow()
    new_status = HelmetStatus.active

    if data.co is not None:
        if data.co > 200:
            db.add(Alert(
                level=AlertLevel.critical,
                type=AlertType.gas,
                message=f"Critical CO level: {data.co:.1f} ppm (threshold: 200 ppm)",
                helmet_id=helmet_id,
                worker_id=helmet.worker_id,
            ))
            new_status = HelmetStatus.critical
        elif data.co > 50:
            db.add(Alert(
                level=AlertLevel.warning,
                type=AlertType.gas,
                message=f"Elevated CO level: {data.co:.1f} ppm (threshold: 50 ppm)",
                helmet_id=helmet_id,
                worker_id=helmet.worker_id,
            ))
            if new_status != HelmetStatus.critical:
                new_status = HelmetStatus.warning

    if data.ch4 is not None:
        if data.ch4 > 2.0:
            db.add(Alert(
                level=AlertLevel.critical,
                type=AlertType.gas,
                message=f"Critical CH4 level: {data.ch4:.2f}% (threshold: 2.0%)",
                helmet_id=helmet_id,
                worker_id=helmet.worker_id,
            ))
            new_status = HelmetStatus.critical
        elif data.ch4 > 1.0:
            db.add(Alert(
                level=AlertLevel.warning,
                type=AlertType.gas,
                message=f"Elevated CH4 level: {data.ch4:.2f}% (threshold: 1.0%)",
                helmet_id=helmet_id,
                worker_id=helmet.worker_id,
            ))
            if new_status != HelmetStatus.critical:
                new_status = HelmetStatus.warning

    if data.temperature is not None:
        if data.temperature > 55:
            db.add(Alert(
                level=AlertLevel.critical,
                type=AlertType.temperature,
                message=f"Critical temperature: {data.temperature:.1f}°C",
                helmet_id=helmet_id,
                worker_id=helmet.worker_id,
            ))
            new_status = HelmetStatus.critical
        elif data.temperature > 40:
            db.add(Alert(
                level=AlertLevel.warning,
                type=AlertType.temperature,
                message=f"High temperature: {data.temperature:.1f}°C",
                helmet_id=helmet_id,
                worker_id=helmet.worker_id,
            ))
            if new_status != HelmetStatus.critical:
                new_status = HelmetStatus.warning

    if data.impactDetected is True:
        db.add(Alert(
            level=AlertLevel.critical,
            type=AlertType.fall,
            message="Impact/fall detected",
            helmet_id=helmet_id,
            worker_id=helmet.worker_id,
        ))
        new_status = HelmetStatus.critical

    if data.helmetWear is False:
        db.add(Alert(
            level=AlertLevel.warning,
            type=AlertType.helmet_off,
            message="Helmet not being worn",
            helmet_id=helmet_id,
            worker_id=helmet.worker_id,
        ))
        if new_status != HelmetStatus.critical:
            new_status = HelmetStatus.warning

    helmet.status = new_status

    await db.commit()
    await db.refresh(reading)
    return reading
