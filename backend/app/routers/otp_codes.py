"""
OTP Code API endpoints.

Endpoints:
  POST  /api/auth/send-otp    — generate & store an OTP, dispatch email
  POST  /api/auth/verify-otp  — verify code, return JWT token
  GET   /api/otp-codes        — list OTP records (admin)
  GET   /api/otp-codes/{id}   — get single OTP record (admin)
  DELETE /api/otp-codes/{id}  — delete OTP record (admin)
"""

import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.otp_code import OtpCode
from app.schemas.otp_code import (
    OtpCodeRead,
    SendOtpRequest,
    SendOtpResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 10
OTP_RATE_LIMIT_PER_HOUR = 5

router = APIRouter(tags=["otp"])


def _generate_otp_code() -> str:
    """Return a cryptographically secure 6-digit OTP string."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _issue_token(email: str) -> str:
    """Issue a simple opaque token. Replace with JWT in production."""
    return secrets.token_hex(32)


@router.post("/api/auth/send-otp", response_model=SendOtpResponse, status_code=200)
def send_otp(
    payload: SendOtpRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    Generate a 6-digit OTP, persist it, and log that an email would be dispatched.

    Rate-limited to OTP_RATE_LIMIT_PER_HOUR requests per email per hour.
    Returns HTTP 429 when the limit is exceeded.
    """
    email = payload.email.lower().strip()
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    recent_count = (
        db.query(OtpCode)
        .filter(OtpCode.email == email, OtpCode.created_at >= one_hour_ago)
        .count()
    )
    if recent_count >= OTP_RATE_LIMIT_PER_HOUR:
        logger.warning("OTP rate limit exceeded for email: %s", email)
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait before trying again.",
        )

    code = _generate_otp_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    otp = OtpCode(email=email, code=code, expires_at=expires_at, used=False)
    db.add(otp)
    db.commit()
    db.refresh(otp)

    # Email dispatch — log only (real mailer wired separately)
    logger.info("OTP %s generated for %s (expires %s)", otp.id, email, expires_at.isoformat())

    return {"message": "If this email is registered, a code has been sent."}


@router.post("/api/auth/verify-otp", response_model=VerifyOtpResponse, status_code=200)
def verify_otp(
    payload: VerifyOtpRequest,
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    """
    Verify the submitted OTP code.

    Returns HTTP 401 when no valid (unused, unexpired) OTP matches.
    On success marks the OTP as used and returns a token.
    """
    email = payload.email.lower().strip()
    now = datetime.now(timezone.utc)

    otp = (
        db.query(OtpCode)
        .filter(
            OtpCode.email == email,
            OtpCode.code == payload.code,
            OtpCode.used.is_(False),
            OtpCode.expires_at > now,
        )
        .order_by(OtpCode.created_at.desc())
        .first()
    )

    if otp is None:
        logger.warning("Failed OTP verification for email: %s", email)
        raise HTTPException(status_code=401, detail="Invalid or expired code.")

    otp.used = True
    db.commit()

    token = _issue_token(email)
    logger.info("User authenticated via OTP: %s", email)

    return {"token": token, "email": email, "expires_in": 86400}


@router.get("/api/otp-codes", response_model=list[OtpCodeRead])
def list_otp_codes(
    db: Annotated[Session, Depends(get_db)],
    email: str | None = Query(default=None),
    used: bool | None = Query(default=None),
) -> list[OtpCode]:
    """List OTP records, optionally filtered by email and/or used status (admin)."""
    query = db.query(OtpCode)
    if email is not None:
        query = query.filter(OtpCode.email == email.lower().strip())
    if used is not None:
        query = query.filter(OtpCode.used.is_(used))
    results = query.order_by(OtpCode.created_at.desc()).all()
    logger.info("Listed %d OTP records (email=%s, used=%s)", len(results), email, used)
    return results


@router.get("/api/otp-codes/{otp_id}", response_model=OtpCodeRead)
def get_otp_code(
    otp_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> OtpCode:
    """Return a single OTP record by UUID (admin)."""
    obj = db.get(OtpCode, otp_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="OTP code not found")
    return obj


@router.delete("/api/otp-codes/{otp_id}", status_code=204)
def delete_otp_code(
    otp_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete an OTP record by UUID (admin)."""
    obj = db.get(OtpCode, otp_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="OTP code not found")
    db.delete(obj)
    db.commit()
    logger.info("OTP record %s deleted", otp_id)
