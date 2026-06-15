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

    @classmethod
    def model_validate(cls, obj, **kwargs):
        # Safely resolve computed properties without triggering lazy loads
        data = super().model_validate(obj, **kwargs)

        def _get(o, attr, default=None):
            if o is None:
                return default
            if isinstance(o, dict):
                return o.get(attr, default)
            return getattr(o, attr, default)

        if getattr(data, "department", None) is None:
            data.department = _get(obj, "zone") or _get(obj, "department")
        if getattr(data, "name", None) is None:
            data.name = _get(obj, "full_name")
        if getattr(data, "email", None) is None:
            user = _get(obj, "user")
            if user is not None:
                data.email = _get(user, "email")
        if getattr(data, "status", None) is None:
            is_active = _get(obj, "is_active")
            data.status = 'active' if is_active else 'inactive'
        return data


class WorkerCreate(BaseModel):
    full_name: str
    employee_id: str
    email: Optional[EmailStr] = None
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
