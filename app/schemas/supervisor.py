import uuid
from pydantic import BaseModel, EmailStr
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


class SupervisorCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    employee_id: Optional[str] = None


class SupervisorUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class SupervisorResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    name: Optional[str] = None
    employee_id: str
    phone: Optional[str] = None
    is_active: bool
    user_id: Optional[uuid.UUID] = None
    user: Optional[UserBrief] = None
    created_at: datetime
    updated_at: datetime

    # Derived from model properties (populated via selectinload)
    email: Optional[str] = None
    status: Optional[str] = None
    worker_count: Optional[int] = 0
    gateway_count: Optional[int] = 0
    last_active: Optional[datetime] = None

    model_config = {"from_attributes": True}
