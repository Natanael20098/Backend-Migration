import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class NotificationCreate(BaseModel):
    user_id: Optional[uuid.UUID] = None
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    type: str = Field(default="INFO", max_length=50)
    link: Optional[str] = Field(default=None, max_length=500)
    user_name: Optional[str] = Field(default=None, max_length=255)
    user_email: Optional[EmailStr] = None


class NotificationRead(BaseModel):
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    title: str
    message: str
    type: str
    is_read: bool
    read_at: Optional[datetime]
    link: Optional[str]
    user_name: Optional[str]
    user_email: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationMarkRead(BaseModel):
    is_read: bool = True
