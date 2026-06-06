import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum

class AlertLevel(str, enum.Enum):
    critical = "critical"
    warning  = "warning"
    info     = "info"

class AlertType(str, enum.Enum):
    gas         = "gas"
    temperature = "temperature"
    fall        = "fall"
    helmet_off  = "helmet_off"
    humidity    = "humidity"
    multi       = "multi"

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    level: Mapped[AlertLevel] = mapped_column(SAEnum(AlertLevel), nullable=False)
    type: Mapped[AlertType]   = mapped_column(SAEnum(AlertType),  nullable=False)
    message: Mapped[str]      = mapped_column(Text, nullable=False)
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[str]      = mapped_column(String(255), nullable=True)

    helmet_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("helmets.id"), nullable=True
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    helmet: Mapped["Helmet"] = relationship("Helmet", back_populates="alerts")
    worker: Mapped["Worker"] = relationship("Worker", back_populates="alerts")