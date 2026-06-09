import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base

class Supervisor(Base):
    __tablename__ = "supervisors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str]   = mapped_column(String(255), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    phone: Mapped[str]       = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool]  = mapped_column(Boolean, default=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    user: Mapped["User"]           = relationship("User")
    workers: Mapped[list["Worker"]]= relationship("Worker", back_populates="supervisor")
    gateways: Mapped[list["Gateway"]] = relationship(
        "Gateway", secondary="supervisor_gateways"
    )

    @property
    def name(self) -> str:
        return self.full_name

    @property
    def email(self) -> Optional[str]:
        return self.user.email if self.user else None

    @property
    def status(self) -> str:
        return 'active' if self.is_active else 'inactive'

    @property
    def worker_count(self) -> int:
        try:
            return len(self.workers) if self.workers is not None else 0
        except Exception:
            return 0

    @property
    def gateway_count(self) -> int:
        try:
            return len(self.gateways) if self.gateways is not None else 0
        except Exception:
            return 0

    @property
    def last_active(self) -> datetime:
        return self.updated_at