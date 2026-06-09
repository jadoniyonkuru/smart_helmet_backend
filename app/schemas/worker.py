import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.user import UserRole


class UserBrief(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    avatar_url: Optional[str] = None
    model_config = {"from_attributes": True}


class WorkerCreate(BaseModel):
    full_name: str
    employee_id: str
    phone: Optional[str] = None
    zone: Optional[str] = None
    supervisor_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None


class WorkerUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    zone: Optional[str] = None
    is_active: Optional[bool] = None
    supervisor_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None


class WorkerResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    name: Optional[str] = None
    employee_id: str
    phone: Optional[str] = None
    zone: Optional[str] = None
    department: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    is_active: bool
    supervisor_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    user: Optional[UserBrief] = None
    created_at: datetime
    updated_at: datetime

    # Derived from model properties
    email: Optional[str] = None
    status: Optional[str] = None

    model_config = {"from_attributes": True}
