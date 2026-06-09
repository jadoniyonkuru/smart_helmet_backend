import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Gateway(Base):
    __tablename__ = "gateways"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str]     = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(50), nullable=True)
    is_online: Mapped[bool]  = mapped_column(Boolean, default=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    packet_delivery_rate: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    helmets: Mapped[list["Helmet"]] = relationship("Helmet", back_populates="gateway")

    @property
    def status(self) -> str:
        return 'online' if self.is_online else 'offline'

    @property
    def last_heartbeat(self) -> Optional[datetime]:
        return self.last_seen

    @property
    def signal_strength(self) -> int:
        val = self.packet_delivery_rate or 0.0
        # stored as 0–100; if accidentally stored as 0.0–1.0, normalise
        if val <= 1.0 and val > 0:
            return int(val * 100)
        return int(val)

    @property
    def connected_helmets(self) -> int:
        try:
            return len(self.helmets) if self.helmets is not None else 0
        except Exception:
            return 0