import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class SensorDataResponse(BaseModel):
    id: uuid.UUID
    helmet_id: uuid.UUID
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    gas_level: Optional[int] = None
    co_ppm: Optional[float] = None
    ch4_percent: Optional[float] = None
    vibration_detected: bool
    helmet_worn: bool
    accelerometer_x: Optional[float] = None
    accelerometer_y: Optional[float] = None
    accelerometer_z: Optional[float] = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


class SensorDataCreate(BaseModel):
    helmet_id: uuid.UUID
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    gas_level: Optional[int] = None
    co_ppm: Optional[float] = None
    ch4_percent: Optional[float] = None
    vibration_detected: bool = False
    helmet_worn: bool = True
    accelerometer_x: Optional[float] = None
    accelerometer_y: Optional[float] = None
    accelerometer_z: Optional[float] = None
