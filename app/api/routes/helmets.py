import uuid
from datetime import datetime
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
from app.models.alert import Alert, AlertLevel, AlertType
from app.models.helmet import HelmetStatus
from app.models.user import User, UserRole
from app.models.supervisor import Supervisor
from app.websockets.manager import manager

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
    helmet = await get_helmet(db, helmet_id)

    reading = SensorData(
        helmet_id=helmet_id,
        co_ppm=data.co,
        ch4_percent=data.ch4,
        temperature=data.temperature,
        humidity=data.humidity,
        helmet_worn=data.helmetWear if data.helmetWear is not None else True,
        vibration_detected=data.impactDetected
        if data.impactDetected is not None
        else False,
        battery_level=data.battery,
        signal_strength=data.signalStrength,
        accelerometer_x=data.accelerometerX,
        accelerometer_y=data.accelerometerY,
        accelerometer_z=data.accelerometerZ,
        gas_level=data.gasLevel,
    )
    # Extended fields from firmware
    reading.gyro_x = data.gyroX
    reading.gyro_y = data.gyroY
    reading.gyro_z = data.gyroZ
    reading.ir_value = data.irValue
    reading.step_count = data.stepCount
    reading.heading_deg = data.headingDeg
    reading.est_zone = data.estZone

    # Run AI inference (synchronous) and attach results to the reading.
    # Import the AI service lazily so the app can start without ML deps installed.
    try:
        from app.services.ai_service import ai_service
    except Exception:
        ai_service = None

    if ai_service and getattr(ai_service, "models_loaded", False):
        try:
            ai_result = ai_service.run_inference(
                {
                    "co_ppm": data.co,
                    "ch4_pct": data.ch4,
                    "temperature_c": data.temperature,
                    "humidity_pct": data.humidity,
                    "helmet_id": str(helmet_id),
                }
            )
        except Exception:
            ai_result = {
                "prediction": "unknown",
                "danger_votes": 0,
                "confidence": 0,
                "model_votes": {},
            }
    else:
        ai_result = {
            "prediction": "unknown",
            "danger_votes": 0,
            "confidence": 0,
            "model_votes": {},
        }

    reading.ai_prediction = ai_result.get("prediction")
    reading.ai_confidence = ai_result.get("confidence")
    reading.ai_danger_votes = ai_result.get("danger_votes")
    mvotes = ai_result.get("model_votes", {})
    reading.ai_if_vote = mvotes.get("isolation_forest")
    reading.ai_rf_vote = mvotes.get("random_forest")
    reading.ai_lstm_vote = mvotes.get("lstm")
    reading.ai_svm_vote = mvotes.get("svm")
    db.add(reading)

    helmet.last_seen = datetime.utcnow()
    new_status = HelmetStatus.active

    if data.co is not None:
        if data.co > 200:
            db.add(
                Alert(
                    level=AlertLevel.critical,
                    type=AlertType.gas,
                    message=f"Critical CO level: {data.co:.1f} ppm (threshold: 200 ppm)",
                    helmet_id=helmet_id,
                    worker_id=helmet.worker_id,
                )
            )
            new_status = HelmetStatus.critical
        elif data.co > 50:
            db.add(
                Alert(
                    level=AlertLevel.warning,
                    type=AlertType.gas,
                    message=f"Elevated CO level: {data.co:.1f} ppm (threshold: 50 ppm)",
                    helmet_id=helmet_id,
                    worker_id=helmet.worker_id,
                )
            )
            if new_status != HelmetStatus.critical:
                new_status = HelmetStatus.warning

    if data.ch4 is not None:
        if data.ch4 > 2.0:
            db.add(
                Alert(
                    level=AlertLevel.critical,
                    type=AlertType.gas,
                    message=f"Critical CH4 level: {data.ch4:.2f}% (threshold: 2.0%)",
                    helmet_id=helmet_id,
                    worker_id=helmet.worker_id,
                )
            )
            new_status = HelmetStatus.critical
        elif data.ch4 > 1.0:
            db.add(
                Alert(
                    level=AlertLevel.warning,
                    type=AlertType.gas,
                    message=f"Elevated CH4 level: {data.ch4:.2f}% (threshold: 1.0%)",
                    helmet_id=helmet_id,
                    worker_id=helmet.worker_id,
                )
            )
            if new_status != HelmetStatus.critical:
                new_status = HelmetStatus.warning

    if data.temperature is not None:
        if data.temperature > 55:
            db.add(
                Alert(
                    level=AlertLevel.critical,
                    type=AlertType.temperature,
                    message=f"Critical temperature: {data.temperature:.1f}°C",
                    helmet_id=helmet_id,
                    worker_id=helmet.worker_id,
                )
            )
            new_status = HelmetStatus.critical
        elif data.temperature > 40:
            db.add(
                Alert(
                    level=AlertLevel.warning,
                    type=AlertType.temperature,
                    message=f"High temperature: {data.temperature:.1f}°C",
                    helmet_id=helmet_id,
                    worker_id=helmet.worker_id,
                )
            )
            if new_status != HelmetStatus.critical:
                new_status = HelmetStatus.warning

    if data.impactDetected is True:
        db.add(
            Alert(
                level=AlertLevel.critical,
                type=AlertType.fall,
                message="Impact/fall detected",
                helmet_id=helmet_id,
                worker_id=helmet.worker_id,
            )
        )
        new_status = HelmetStatus.critical

    if data.helmetWear is False:
        db.add(
            Alert(
                level=AlertLevel.warning,
                type=AlertType.helmet_off,
                message="Helmet not being worn",
                helmet_id=helmet_id,
                worker_id=helmet.worker_id,
            )
        )
        if new_status != HelmetStatus.critical:
            new_status = HelmetStatus.warning

    helmet.status = new_status

    # If AI predicted danger, create AI alert
    if reading.ai_prediction == "danger":
        dv = int(reading.ai_danger_votes or 0)
        level = AlertLevel.critical if dv >= 3 else AlertLevel.warning
        mv = mvotes
        msg_parts = [
            f"AI detected danger ({dv}/4 models). Confidence: {reading.ai_confidence or 0:.1f}%"
        ]
        votes_str = " ".join(
            [
                f"IF:{mv.get('isolation_forest', 'unknown')}",
                f"RF:{mv.get('random_forest', 'unknown')}",
                f"LSTM:{mv.get('lstm', 'unknown')}",
                f"SVM:{mv.get('svm', 'unknown')}",
            ]
        )
        msg_parts.append(votes_str)
        alert = Alert(
            level=level,
            type=AlertType.multi,
            message=" - ".join(msg_parts),
            helmet_id=helmet_id,
            worker_id=helmet.worker_id,
        )
        db.add(alert)
        # Mark status accordingly
        if level == AlertLevel.critical:
            helmet.status = HelmetStatus.critical

    await db.commit()
    await db.refresh(reading)

    # Push websocket update to helmet room
    try:
        room = f"helmet_{helmet_id}"
        await manager.broadcast(
            {
                "co": reading.co_ppm,
                "ch4": reading.ch4_percent,
                "temperature": reading.temperature,
                "humidity": reading.humidity,
                "helmetWear": reading.helmet_worn,
                "impactDetected": reading.vibration_detected,
                "battery": reading.battery_level,
                "signalStrength": reading.signal_strength,
                "accelerometerX": reading.accelerometer_x,
                "accelerometerY": reading.accelerometer_y,
                "accelerometerZ": reading.accelerometer_z,
                "stepCount": reading.step_count,
                "headingDeg": reading.heading_deg,
                "estZone": reading.est_zone,
                "aiPrediction": reading.ai_prediction,
                "aiConfidence": reading.ai_confidence,
                "aiDangerVotes": reading.ai_danger_votes,
                "aiModelVotes": {
                    "isolationForest": reading.ai_if_vote,
                    "randomForest": reading.ai_rf_vote,
                    "lstm": reading.ai_lstm_vote,
                    "svm": reading.ai_svm_vote,
                },
            },
            room=room,
        )
    except Exception:
        pass

    # Push alert summary to alerts room (if created)
    try:
        async with db.begin():
            result = await db.execute(
                select(Alert)
                .where(Alert.helmet_id == helmet_id)
                .order_by(Alert.created_at.desc())
                .limit(1)
            )
            last_alert = result.scalar_one_or_none()
        if last_alert:
            await manager.broadcast(
                {
                    "type": "new_alert",
                    "alert": {
                        "id": str(last_alert.id),
                        "helmet_id": str(last_alert.helmet_id)
                        if last_alert.helmet_id
                        else None,
                        "type": last_alert.type.value,
                        "level": last_alert.level.value,
                        "message": last_alert.message,
                        "timestamp": last_alert.created_at.isoformat(),
                        "resolved": last_alert.is_resolved,
                    },
                },
                room="alerts",
            )
    except Exception:
        pass

    return reading
