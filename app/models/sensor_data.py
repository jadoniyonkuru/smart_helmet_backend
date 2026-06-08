import uuid
from datetime import datetime
from sqlalchemy import Float, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    helmet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("helmets.id"), nullable=False
    )

    # DHT22
    temperature: Mapped[float] = mapped_column(Float, nullable=True)
    humidity: Mapped[float]    = mapped_column(Float, nullable=True)

    # MQ-2 Gas sensor
    gas_level: Mapped[int]     = mapped_column(Integer, nullable=True)
    co_ppm: Mapped[float]      = mapped_column(Float, nullable=True)
    ch4_percent: Mapped[float] = mapped_column(Float, nullable=True)

    # Vibration / Fall
    vibration_detected: Mapped[bool] = mapped_column(Boolean, default=False)

    # FSR — helmet worn
    helmet_worn: Mapped[bool] = mapped_column(Boolean, default=True)

    # IMU
    accelerometer_x: Mapped[float] = mapped_column(Float, nullable=True)
    accelerometer_y: Mapped[float] = mapped_column(Float, nullable=True)
    accelerometer_z: Mapped[float] = mapped_column(Float, nullable=True)

    # Device health
    battery_level: Mapped[float]   = mapped_column(Float, nullable=True)   # percentage 0–100
    signal_strength: Mapped[int]   = mapped_column(Integer, nullable=True) # RSSI dBm

    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    helmet: Mapped["Helmet"] = relationship("Helmet", back_populates="sensor_data")