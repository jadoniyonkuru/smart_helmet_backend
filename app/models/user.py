import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base
import enum

class UserRole(str, enum.Enum):
    admin      = "admin"
    supervisor = "supervisor"
    worker     = "worker"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str]    = mapped_column(String(255), unique=True, nullable=False)
    full_name: Mapped[str]= mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole]= mapped_column(SAEnum(UserRole), default=UserRole.worker)
    is_active: Mapped[bool]   = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    reset_token: Mapped[str]  = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str]   = mapped_column(String(500), nullable=True)
    phone: Mapped[str]        = mapped_column(String(30), nullable=True)
    location: Mapped[str]     = mapped_column(String(255), nullable=True)
    department: Mapped[str]   = mapped_column(String(255), nullable=True)
    bio: Mapped[str]          = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def name(self) -> str:
        return self.full_name