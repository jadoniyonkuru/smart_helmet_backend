import asyncio
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.sensor_data import SensorData
from app.models.alert import Alert
from app.models.gateway import Gateway
from app.websockets.manager import manager

router = APIRouter()


@router.websocket("/helmets/{helmet_id}")
async def helmet_ws(websocket: WebSocket, helmet_id: uuid.UUID):
    room = f"helmet_{helmet_id}"
    await manager.connect(websocket, room)
    try:
        while True:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(SensorData)
                    .where(SensorData.helmet_id == helmet_id)
                    .order_by(SensorData.recorded_at.desc())
                    .limit(1)
                )
                data = result.scalar_one_or_none()
            if data:
                await websocket.send_json(
                    {
                        "helmet_id": str(helmet_id),
                        "temperature": data.temperature,
                        "humidity": data.humidity,
                        "gas_level": data.gas_level,
                        "co_ppm": data.co_ppm,
                        "ch4_percent": data.ch4_percent,
                        "vibration_detected": data.vibration_detected,
                        "helmet_worn": data.helmet_worn,
                        "accelerometer_x": data.accelerometer_x,
                        "accelerometer_y": data.accelerometer_y,
                        "accelerometer_z": data.accelerometer_z,
                        "gyro_x": data.gyro_x,
                        "gyro_y": data.gyro_y,
                        "gyro_z": data.gyro_z,
                        "ir_value": data.ir_value,
                        "battery_level": data.battery_level,
                        "signal_strength": data.signal_strength,
                        "step_count": data.step_count,
                        "heading_deg": data.heading_deg,
                        "est_zone": data.est_zone,
                        "ai_prediction": data.ai_prediction,
                        "ai_confidence": data.ai_confidence,
                        "ai_danger_votes": data.ai_danger_votes,
                        "ai_model_votes": {
                            "isolation_forest": data.ai_if_vote,
                            "random_forest": data.ai_rf_vote,
                            "lstm": data.ai_lstm_vote,
                            "svm": data.ai_svm_vote,
                        },
                        "recorded_at": data.recorded_at.isoformat(),
                    }
                )
            else:
                await websocket.send_json(
                    {"helmet_id": str(helmet_id), "message": "No sensor data yet"}
                )
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room)


@router.websocket("/alerts")
async def alerts_ws(websocket: WebSocket):
    await manager.connect(websocket, "alerts")
    try:
        while True:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(Alert)
                    .where(Alert.is_resolved == False)
                    .order_by(Alert.created_at.desc())
                    .limit(10)
                )
                alerts = result.scalars().all()
            await websocket.send_json(
                {
                    "type": "unresolved_alerts",
                    "count": len(alerts),
                    "alerts": [
                        {
                            "id": str(a.id),
                            "level": a.level.value,
                            "type": a.type.value,
                            "message": a.message,
                            "helmet_id": str(a.helmet_id) if a.helmet_id else None,
                            "created_at": a.created_at.isoformat(),
                        }
                        for a in alerts
                    ],
                }
            )
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "alerts")


@router.websocket("/gateways")
async def gateways_ws(websocket: WebSocket):
    await manager.connect(websocket, "gateways")
    try:
        while True:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Gateway))
                gateways = result.scalars().all()
            await websocket.send_json(
                {
                    "type": "gateway_status",
                    "gateways": [
                        {
                            "id": str(g.id),
                            "name": g.name,
                            "is_online": g.is_online,
                            "location": g.location,
                            "ip_address": g.ip_address,
                            "packet_delivery_rate": g.packet_delivery_rate,
                            "last_seen": g.last_seen.isoformat()
                            if g.last_seen
                            else None,
                        }
                        for g in gateways
                    ],
                }
            )
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "gateways")
