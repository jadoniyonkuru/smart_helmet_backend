import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum

class HelmetStatus(str, enum.Enum):
    active   = "active"
    inactive = "inactive"
    critical = "critical"
    warning  = "warning"

class Helmet(Base):
    __tablename__ = "helmets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    helmet_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[HelmetStatus] = mapped_column(
        SAEnum(HelmetStatus), default=HelmetStatus.inactive
    )
    zone: Mapped[str]        = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool]  = mapped_column(Boolean, default=True)
    firmware_version: Mapped[str] = mapped_column(String(50), nullable=True)
    last_seen: Mapped[datetime]   = mapped_column(DateTime, nullable=True)

    gateway_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("gateways.id"), nullable=True
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    gateway: Mapped["Gateway"]       = relationship("Gateway", back_populates="helmets")
    worker: Mapped["Worker"]         = relationship("Worker", back_populates="helmets")
    sensor_data: Mapped[list["SensorData"]] = relationship(
        "SensorData", back_populates="helmet"
    )
    alerts: Mapped[list["Alert"]]    = relationship("Alert", back_populates="helmet")

    @property
    def worker_name(self) -> Optional[str]:
        return self.worker.full_name if self.worker else None