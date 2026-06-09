import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.helmet import HelmetStatus


class HelmetCreate(BaseModel):
    helmet_code: str
    zone: Optional[str] = None
    firmware_version: Optional[str] = None
    gateway_id: Optional[uuid.UUID] = None
    worker_id: Optional[uuid.UUID] = None


class HelmetUpdate(BaseModel):
    zone: Optional[str] = None
    status: Optional[HelmetStatus] = None
    firmware_version: Optional[str] = None
    gateway_id: Optional[uuid.UUID] = None
    worker_id: Optional[uuid.UUID] = None
    is_active: Optional[bool] = None


class HelmetResponse(BaseModel):
    id: uuid.UUID
    helmet_code: str
    status: HelmetStatus
    zone: Optional[str] = None
    is_active: bool
    firmware_version: Optional[str] = None
    last_seen: Optional[datetime] = None
    gateway_id: Optional[uuid.UUID] = None
    worker_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    # Derived from relationships
    worker_name: Optional[str] = None

    model_config = {"from_attributes": True}
