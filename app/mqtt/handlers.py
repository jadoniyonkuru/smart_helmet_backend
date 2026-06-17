"""
MQTT message handlers.

Topic convention (firmware):
  safehelm/helmets/<numeric-id>/readings  — ESP32 publishes sensor data here

Firmware sends snake_case JSON; this handler transforms it to the
camelCase format that process_helmet_reading expects.
"""
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.services.reading_processor import process_helmet_reading

logger = logging.getLogger(__name__)

# Dedicated DB engine for MQTT — independent from the HTTP request sessions.
_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_Session = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

# Map firmware numeric helmet IDs → database UUIDs.
# Add one entry per physical helmet device.
HELMET_ID_MAP: dict[str, uuid.UUID] = {
    "1": uuid.UUID("6155cbb1-3fb9-4d7c-a165-fb77ac822b63"),
}


def _transform(fw: dict) -> dict:
    """Convert firmware snake_case JSON to backend camelCase format."""
    return {
        "co":             fw.get("co_ppm", 0),
        "ch4":            fw.get("ch4_pct", 0),
        "gasLevel":       fw.get("co_ppm", 0),
        "temperature":    fw.get("temperature_c", 0),
        "humidity":       fw.get("humidity_pct", 0),
        "helmetWear":     fw.get("helmet_worn", True),
        "impactDetected": fw.get("alert_fall", False),
        "battery":        100.0,
        "signalStrength": fw.get("rssi", -50),
        "accelerometerX": fw.get("accel_x", 0),
        "accelerometerY": fw.get("accel_y", 0),
        "accelerometerZ": fw.get("accel_z", 0),
        "gyroX":          fw.get("gyro_x", 0),
        "gyroY":          fw.get("gyro_y", 0),
        "gyroZ":          fw.get("gyro_z", 0),
        "irValue":        fw.get("ir_value", 0),
        "stepCount":      fw.get("step_count", 0),
        "headingDeg":     fw.get("heading_deg", 0),
        "estZone":        fw.get("est_zone", "Unknown"),
    }


async def on_helmet_reading(topic: str, payload: dict) -> None:
    """
    Called when a message arrives on safehelm/helmets/+/readings.
    Topic format: safehelm/helmets/<numeric-id>/readings
    """
    parts = topic.split("/")
    if len(parts) != 4:
        logger.warning("[MQTT] Unexpected topic format: %s", topic)
        return

    helmet_num = parts[2]
    helmet_id  = HELMET_ID_MAP.get(helmet_num)
    if not helmet_id:
        logger.warning(
            "[MQTT] No UUID configured for helmet ID '%s' — add it to HELMET_ID_MAP",
            helmet_num,
        )
        return

    backend_data = _transform(payload)

    logger.debug("[MQTT] Reading received for helmet %s (id=%s)", helmet_id, helmet_num)
    try:
        async with _Session() as db:
            await process_helmet_reading(db, helmet_id, backend_data)
        logger.debug("[MQTT] Reading processed for helmet %s", helmet_id)
    except Exception:
        logger.exception("[MQTT] Error processing reading for helmet %s", helmet_id)
