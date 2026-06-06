import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SupervisorCreate(BaseModel):
    full_name: str
    employee_id: str
    phone: Optional[str] = None
    user_id: Optional[uuid.UUID] = None


class SupervisorUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class SupervisorResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    employee_id: str
    phone: Optional[str] = None
    is_active: bool
    user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
