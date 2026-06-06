import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WorkerCreate(BaseModel):
    full_name: str
    employee_id: str
    phone: Optional[str] = None
    zone: Optional[str] = None
    supervisor_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None


class WorkerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    zone: Optional[str] = None
    is_active: Optional[bool] = None
    supervisor_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None


class WorkerResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    employee_id: str
    phone: Optional[str] = None
    zone: Optional[str] = None
    is_active: bool
    supervisor_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
