import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.alert import AlertLevel, AlertType


class AlertCreate(BaseModel):
    level: AlertLevel
    type: AlertType
    message: str
    helmet_id: Optional[uuid.UUID] = None
    worker_id: Optional[uuid.UUID] = None


class AlertResolve(BaseModel):
    resolved_by: str


class AlertResponse(BaseModel):
    id: uuid.UUID
    level: AlertLevel
    type: AlertType
    message: str
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    helmet_id: Optional[uuid.UUID] = None
    worker_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}
