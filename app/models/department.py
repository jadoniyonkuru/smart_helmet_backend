import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str]        = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    location: Mapped[Optional[str]]    = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool]  = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    workers: Mapped[list["Worker"]] = relationship("Worker", back_populates="dept")

    @property
    def worker_count(self) -> int:
        try:
            return len(self.workers) if self.workers is not None else 0
        except Exception:
            return 0

    @property
    def status(self) -> str:
        return "active" if self.is_active else "inactive"
