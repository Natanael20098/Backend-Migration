import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AuditLogCreate(BaseModel):
    action: str = Field(..., min_length=1, max_length=100)
    entity_type: str = Field(..., min_length=1, max_length=100)
    entity_id: Optional[str] = Field(default=None, max_length=255)
    user_id: Optional[str] = Field(default=None, max_length=255)
    user_email: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = None
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)


class AuditLogRead(BaseModel):
    id: uuid.UUID
    action: str
    entity_type: str
    entity_id: Optional[str]
    user_id: Optional[str]
    user_email: Optional[str]
    description: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogPage(BaseModel):
    items: list[AuditLogRead]
    total: int
    page: int
    size: int
    pages: int
