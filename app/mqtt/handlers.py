"""
MQTT message handlers.

Topic convention:
  helmets/<helmet-uuid>/readings   — ESP32 publishes sensor data here
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


async def on_helmet_reading(topic: str, payload: dict) -> None:
    """
    Called when a message arrives on  helmets/+/readings.

    The ESP32 must publish JSON with these camelCase keys:
        co, ch4, temperature, humidity, helmetWear, impactDetected,
        battery, signalStrength, accelerometerX, accelerometerY, accelerometerZ,
        gasLevel, gyroX, gyroY, gyroZ, irValue, stepCount, headingDeg, estZone
    """
    parts = topic.split("/")
    if len(parts) != 3:
        logger.warning("[MQTT] Unexpected topic format: %s", topic)
        return

    try:
        helmet_id = uuid.UUID(parts[1])
    except ValueError:
        logger.warning("[MQTT] Invalid helmet UUID in topic: %s", parts[1])
        return

    logger.debug("[MQTT] Reading received for helmet %s", helmet_id)
    try:
        async with _Session() as db:
            await process_helmet_reading(db, helmet_id, payload)
        logger.debug("[MQTT] Reading processed for helmet %s", helmet_id)
    except Exception:
        logger.exception("[MQTT] Error processing reading for helmet %s", helmet_id)
