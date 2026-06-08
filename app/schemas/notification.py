import uuid
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.notification import NotificationType


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    type: NotificationType
    is_read: bool
    related_helmet_id: Optional[uuid.UUID] = None
    related_alert_id:  Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}
