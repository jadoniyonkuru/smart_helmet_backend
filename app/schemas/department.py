import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    location: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    is_active: Optional[bool] = None


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    location: Optional[str] = None
    is_active: bool
    worker_count: int = 0
    status: str = "active"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
