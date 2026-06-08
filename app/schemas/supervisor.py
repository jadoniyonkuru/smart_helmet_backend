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
    user: Optional[UserBrief] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
