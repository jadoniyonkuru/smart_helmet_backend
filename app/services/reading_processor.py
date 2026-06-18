"""
Shared sensor-reading processing logic.
Called by both the HTTP route and the MQTT subscriber so the logic stays in one place.
"""
import uuid
import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.sensor_data import SensorData
from app.models.helmet import Helmet, HelmetStatus
from app.models.alert import Alert, AlertLevel, AlertType
from app.models.notification import Notification, NotificationType
from app.websockets.manager import manager

logger = logging.getLogger(__name__)


async def process_helmet_reading(
    db: AsyncSession,
    helmet_id: uuid.UUID,
    data: dict,
) -> SensorData:
    """
    Process one sensor reading from any source (HTTP POST or MQTT).

    `data` must use the same camelCase keys the ESP32 firmware sends:
        co, ch4, temperature, humidity, helmetWear, impactDetected,
        battery, signalStrength, accelerometerX/Y/Z, gasLevel,
        gyroX/Y/Z, irValue, stepCount, headingDeg, estZone
    """
    from app.services.helmet_service import get_helmet

    helmet = await get_helmet(db, helmet_id)

    reading = SensorData(
        helmet_id=helmet_id,
        co_ppm=data.get("co"),
        ch4_percent=data.get("ch4"),
        temperature=data.get("temperature"),
        humidity=data.get("humidity"),
        helmet_worn=data.get("helmetWear") if data.get("helmetWear") is not None else True,
        vibration_detected=data.get("impactDetected") if data.get("impactDetected") is not None else False,
        battery_level=data.get("battery"),
        signal_strength=data.get("signalStrength"),
        accelerometer_x=data.get("accelerometerX"),
        accelerometer_y=data.get("accelerometerY"),
        accelerometer_z=data.get("accelerometerZ"),
        gas_level=data.get("gasLevel"),
    )
    reading.gyro_x = data.get("gyroX")
    reading.gyro_y = data.get("gyroY")
    reading.gyro_z = data.get("gyroZ")
    reading.ir_value = data.get("irValue")
    reading.step_count = data.get("stepCount")
    reading.heading_deg = data.get("headingDeg")
    reading.est_zone = data.get("estZone")

    # ── AI inference ─────────────────────────────────────────────────────────
    try:
        from app.services.ai_service import ai_service
    except Exception:
        ai_service = None

    if ai_service and getattr(ai_service, "models_loaded", False):
        try:
            ai_result = ai_service.run_inference({
                "co_ppm": data.get("co"),
                "ch4_pct": data.get("ch4"),
                "temperature_c": data.get("temperature"),
                "humidity_pct": data.get("humidity"),
                "helmet_id": str(helmet_id),
            })
        except Exception:
            ai_result = {"prediction": "unknown", "danger_votes": 0, "confidence": 0, "model_votes": {}}
    else:
        ai_result = {"prediction": "unknown", "danger_votes": 0, "confidence": 0, "model_votes": {}}

    raw_ai_prediction = ai_result.get("prediction")
    reading.ai_prediction = raw_ai_prediction
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

    # ── Resolve supervisor user_id for notifications ──────────────────────────
    supervisor_user_id = None
    if helmet.worker_id:
        from app.models.worker import Worker
        from app.models.supervisor import Supervisor
        _res = await db.execute(
            select(Supervisor.user_id)
            .join(Worker, Worker.supervisor_id == Supervisor.id)
            .where(Worker.id == helmet.worker_id)
        )
        supervisor_user_id = _res.scalar_one_or_none()

    def _notify(title: str, message: str, ntype: NotificationType) -> None:
        if supervisor_user_id:
            db.add(Notification(
                user_id=supervisor_user_id,
                title=title,
                message=message,
                type=ntype,
                related_helmet_id=helmet_id,
            ))

    # ── Threshold alerts ──────────────────────────────────────────────────────
    co = data.get("co")
    ch4 = data.get("ch4")
    temperature = data.get("temperature")
    impact = data.get("impactDetected")
    helmet_wear = data.get("helmetWear")

    if co is not None:
        if co > 200:
            db.add(Alert(
                level=AlertLevel.critical, type=AlertType.gas,
                message=f"Critical CO level: {co:.1f} ppm (threshold: 200 ppm)",
                helmet_id=helmet_id, worker_id=helmet.worker_id,
            ))
            _notify("Critical CO Alert", f"CO level is {co:.1f} ppm — exceeds 200 ppm limit.", NotificationType.critical)
            new_status = HelmetStatus.critical
        elif co > 50:
            db.add(Alert(
                level=AlertLevel.warning, type=AlertType.gas,
                message=f"Elevated CO level: {co:.1f} ppm (threshold: 50 ppm)",
                helmet_id=helmet_id, worker_id=helmet.worker_id,
            ))
            _notify("CO Warning", f"CO level is {co:.1f} ppm — exceeds 50 ppm threshold.", NotificationType.warning)
            if new_status != HelmetStatus.critical:
                new_status = HelmetStatus.warning

    if ch4 is not None:
        if ch4 > 2.0:
            db.add(Alert(
                level=AlertLevel.critical, type=AlertType.gas,
                message=f"Critical CH4 level: {ch4:.2f}% (threshold: 2.0%)",
                helmet_id=helmet_id, worker_id=helmet.worker_id,
            ))
            _notify("Critical CH4 Alert", f"CH4 level is {ch4:.2f}% — exceeds 2.0% limit.", NotificationType.critical)
            new_status = HelmetStatus.critical
        elif ch4 > 1.0:
            db.add(Alert(
                level=AlertLevel.warning, type=AlertType.gas,
                message=f"Elevated CH4 level: {ch4:.2f}% (threshold: 1.0%)",
                helmet_id=helmet_id, worker_id=helmet.worker_id,
            ))
            _notify("CH4 Warning", f"CH4 level is {ch4:.2f}% — exceeds 1.0% threshold.", NotificationType.warning)
            if new_status != HelmetStatus.critical:
                new_status = HelmetStatus.warning

    if temperature is not None:
        if temperature > 55:
            db.add(Alert(
                level=AlertLevel.critical, type=AlertType.temperature,
                message=f"Critical temperature: {temperature:.1f}°C",
                helmet_id=helmet_id, worker_id=helmet.worker_id,
            ))
            _notify("Critical Temperature", f"Temperature is {temperature:.1f}°C — exceeds 55°C limit.", NotificationType.critical)
            new_status = HelmetStatus.critical
        elif temperature > 40:
            db.add(Alert(
                level=AlertLevel.warning, type=AlertType.temperature,
                message=f"High temperature: {temperature:.1f}°C",
                helmet_id=helmet_id, worker_id=helmet.worker_id,
            ))
            _notify("High Temperature", f"Temperature is {temperature:.1f}°C — exceeds 40°C threshold.", NotificationType.warning)
            if new_status != HelmetStatus.critical:
                new_status = HelmetStatus.warning

    if impact is True:
        db.add(Alert(
            level=AlertLevel.critical, type=AlertType.fall,
            message="Impact/fall detected",
            helmet_id=helmet_id, worker_id=helmet.worker_id,
        ))
        _notify("Impact Detected", "A fall or impact event was detected on a worker's helmet.", NotificationType.critical)
        new_status = HelmetStatus.critical

    if helmet_wear is False:
        db.add(Alert(
            level=AlertLevel.warning, type=AlertType.helmet_off,
            message="Helmet not being worn",
            helmet_id=helmet_id, worker_id=helmet.worker_id,
        ))
        _notify("Helmet Not Worn", "A worker is not wearing their helmet.", NotificationType.warning)
        if new_status != HelmetStatus.critical:
            new_status = HelmetStatus.warning

    helmet.status = new_status

    # ── Overall AI Prediction ──────────────────────────────────────────────────
    # The trained ensemble only sees gas/temperature/humidity, so it can never flag
    # danger from vibration or a removed helmet on its own. Fold those direct safety
    # signals into the displayed verdict so "AI Prediction" reflects real risk.
    reading.ai_prediction = "danger" if (
        raw_ai_prediction == "danger"
        or impact is True
        or helmet_wear is False
        or new_status == HelmetStatus.critical
    ) else "safe"

    # ── AI danger alert ───────────────────────────────────────────────────────
    # Keyed on the raw ensemble verdict only, so vibration/helmet-off events (which
    # already raise their own alert+notification above) don't get a duplicate one.
    if raw_ai_prediction == "danger":
        dv = int(reading.ai_danger_votes or 0)
        level = AlertLevel.critical if dv >= 3 else AlertLevel.warning
        votes_str = " ".join([
            f"IF:{mvotes.get('isolation_forest', 'unknown')}",
            f"RF:{mvotes.get('random_forest', 'unknown')}",
            f"LSTM:{mvotes.get('lstm', 'unknown')}",
            f"SVM:{mvotes.get('svm', 'unknown')}",
        ])
        ai_alert = Alert(
            level=level, type=AlertType.multi,
            message=f"AI detected danger ({dv}/4 models). Confidence: {reading.ai_confidence or 0:.1f}% - {votes_str}",
            helmet_id=helmet_id, worker_id=helmet.worker_id,
        )
        db.add(ai_alert)
        ntype = NotificationType.critical if level == AlertLevel.critical else NotificationType.warning
        _notify("AI Danger Detected", f"AI flagged danger ({dv}/4 models, {reading.ai_confidence or 0:.1f}% confidence).", ntype)
        if level == AlertLevel.critical:
            helmet.status = HelmetStatus.critical

    await db.commit()
    await db.refresh(reading)

    # ── WebSocket: live sensor data ───────────────────────────────────────────
    try:
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
            room=f"helmet_{helmet_id}",
        )
    except Exception:
        pass

    # ── WebSocket: latest alert ───────────────────────────────────────────────
    try:
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
                        "helmet_id": str(last_alert.helmet_id) if last_alert.helmet_id else None,
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
