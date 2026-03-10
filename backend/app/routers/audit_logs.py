"""
AuditLog API endpoints.

Endpoints:
  POST  /api/audit-logs   — create an audit log entry
  GET   /api/audit-logs   — list audit logs with pagination
"""

import logging
import math
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate, AuditLogPage, AuditLogRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/audit-logs", tags=["audit-logs"])


@router.post("", response_model=AuditLogRead, status_code=201)
def create_audit_log(
    payload: AuditLogCreate,
    db: Annotated[Session, Depends(get_db)],
) -> AuditLog:
    """Store a new audit log entry."""
    entry = AuditLog(
        action=payload.action,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        user_id=payload.user_id,
        user_email=payload.user_email,
        description=payload.description,
        ip_address=payload.ip_address,
        user_agent=payload.user_agent,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    logger.info(
        "AuditLog created: id=%s action=%s entity_type=%s",
        entry.id,
        entry.action,
        entry.entity_type,
    )
    return entry


@router.get("", response_model=AuditLogPage)
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    action: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    user_id: Optional[str] = Query(default=None),
) -> AuditLogPage:
    """Return paginated audit logs, optionally filtered by action, entity_type, or user_id."""
    query = db.query(AuditLog)
    if action is not None:
        query = query.filter(AuditLog.action == action)
    if entity_type is not None:
        query = query.filter(AuditLog.entity_type == entity_type)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)

    total = query.count()
    pages = max(1, math.ceil(total / size))
    offset = (page - 1) * size
    items = query.order_by(AuditLog.created_at.desc()).offset(offset).limit(size).all()

    logger.info(
        "Listed audit logs: total=%d page=%d size=%d", total, page, size
    )
    return AuditLogPage(items=items, total=total, page=page, size=size, pages=pages)
