import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    full_name: Mapped[str]   = mapped_column(String(255), nullable=False)
    employee_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    phone: Mapped[str]       = mapped_column(String(20), nullable=True)
    zone: Mapped[str]        = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool]  = mapped_column(Boolean, default=True)

    supervisor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("supervisors.id"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    supervisor: Mapped["Supervisor"] = relationship(
        "Supervisor", back_populates="workers"
    )
    user:    Mapped["User"]          = relationship("User")
    helmets: Mapped[list["Helmet"]]  = relationship("Helmet", back_populates="worker")
    alerts: Mapped[list["Alert"]]    = relationship("Alert", back_populates="worker")

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
    def department(self) -> Optional[str]:
        return self.zone