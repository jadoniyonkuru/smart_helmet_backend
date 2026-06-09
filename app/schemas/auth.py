import uuid
from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional
from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.supervisor


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    name: Optional[str] = None
    role: UserRole
    is_active: bool
    is_verified: bool
    avatar_url: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    bio: Optional[str] = None

    model_config = {"from_attributes": True}

    @model_validator(mode='after')
    def _set_name(self):
        if not self.name:
            self.name = self.full_name
        return self


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UpdateMeRequest(BaseModel):
    name: Optional[str] = None
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    department: Optional[str] = None
    bio: Optional[str] = None
