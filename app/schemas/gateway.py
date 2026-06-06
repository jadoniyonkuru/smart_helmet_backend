import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GatewayCreate(BaseModel):
    name: str
    location: Optional[str] = None
    ip_address: Optional[str] = None


class GatewayUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    is_online: Optional[bool] = None


class GatewayResponse(BaseModel):
    id: uuid.UUID
    name: str
    location: Optional[str] = None
    ip_address: Optional[str] = None
    is_online: bool
    last_seen: Optional[datetime] = None
    packet_delivery_rate: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
