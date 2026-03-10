import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PropertyImageRead(BaseModel):
    id: uuid.UUID
    property_id: str
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    file_path: str
    caption: Optional[str]
    display_order: Optional[int]
    uploaded_by: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
