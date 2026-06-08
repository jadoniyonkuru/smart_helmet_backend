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
    battery_level: Optional[float] = None
    signal_strength: Optional[int] = None
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
    battery_level: Optional[float] = None
    signal_strength: Optional[int] = None


class HelmetReadingCreate(BaseModel):
    """IoT device payload — camelCase field names from the hardware."""
    co: Optional[float] = None             # maps to co_ppm
    ch4: Optional[float] = None            # maps to ch4_percent
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    helmetWear: Optional[bool] = None      # maps to helmet_worn
    impactDetected: Optional[bool] = None  # maps to vibration_detected
    battery: Optional[float] = None        # maps to battery_level
    signalStrength: Optional[int] = None   # maps to signal_strength
    accelerometerX: Optional[float] = None # maps to accelerometer_x
    accelerometerY: Optional[float] = None # maps to accelerometer_y
    accelerometerZ: Optional[float] = None # maps to accelerometer_z
    gasLevel: Optional[int] = None         # maps to gas_level
