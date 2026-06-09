import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GatewayCreate(BaseModel):
    name: str
    location: Optional[str] = None
    ip_address: Optional[str] = None
    status: Optional[str] = None  # 'online' | 'offline' — mapped to is_online in route


class GatewayUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    ip_address: Optional[str] = None
    is_online: Optional[bool] = None
    status: Optional[str] = None  # 'online' | 'offline' — mapped to is_online in route


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

    # Derived from model properties
    status: Optional[str] = None
    last_heartbeat: Optional[datetime] = None
    signal_strength: int = 0
    connected_helmets: int = 0

    model_config = {"from_attributes": True}
