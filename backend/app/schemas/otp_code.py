import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class SendOtpRequest(BaseModel):
    email: EmailStr


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class OtpCodeRead(BaseModel):
    id: uuid.UUID
    email: str
    expires_at: datetime
    used: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SendOtpResponse(BaseModel):
    message: str


class VerifyOtpResponse(BaseModel):
    token: str
    email: str
    expires_in: int
