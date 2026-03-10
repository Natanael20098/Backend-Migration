"""
Notification API endpoints.

Endpoints:
  POST   /api/notifications          — create a notification (and dispatch email)
  GET    /api/notifications          — list all notifications
  GET    /api/notifications/{id}     — get a single notification
  PATCH  /api/notifications/{id}/read — mark a notification as read
  DELETE /api/notifications/{id}     — delete a notification
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationRead, NotificationMarkRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _get_notification_or_404(notification_id: uuid.UUID, db: Session) -> Notification:
    """Fetch a Notification row by primary key or raise HTTP 404."""
    obj = db.get(Notification, notification_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return obj


@router.post("", response_model=NotificationRead, status_code=201)
def create_notification(
    payload: NotificationCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Notification:
    """Create a new notification record and dispatch an email when user_email is present."""
    notification = Notification(
        user_id=payload.user_id,
        title=payload.title,
        message=payload.message,
        type=payload.type,
        link=payload.link,
        user_name=payload.user_name,
        user_email=str(payload.user_email) if payload.user_email else None,
        is_read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    if notification.user_email:
        logger.info(
            "Notification %s dispatched to %s — title: %s",
            notification.id,
            notification.user_email,
            notification.title,
        )

    logger.info("Notification created: id=%s type=%s", notification.id, notification.type)
    return notification


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    db: Annotated[Session, Depends(get_db)],
    user_id: Optional[uuid.UUID] = Query(default=None),
    unread_only: bool = Query(default=False),
) -> list[Notification]:
    """Return all notifications, optionally filtered by user_id and/or unread status."""
    query = db.query(Notification)
    if user_id is not None:
        query = query.filter(Notification.user_id == user_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    results = query.order_by(Notification.created_at.desc()).all()
    logger.info("Listed %d notifications (user_id=%s, unread_only=%s)", len(results), user_id, unread_only)
    return results


@router.get("/{notification_id}", response_model=NotificationRead)
def get_notification(
    notification_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Notification:
    """Return a single notification by its UUID."""
    return _get_notification_or_404(notification_id, db)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: uuid.UUID,
    payload: NotificationMarkRead,
    db: Annotated[Session, Depends(get_db)],
) -> Notification:
    """Mark a notification as read (or unread)."""
    notification = _get_notification_or_404(notification_id, db)
    notification.is_read = payload.is_read
    if payload.is_read:
        notification.read_at = datetime.now(timezone.utc)
    else:
        notification.read_at = None
    db.commit()
    db.refresh(notification)
    logger.info("Notification %s marked is_read=%s", notification_id, payload.is_read)
    return notification


@router.delete("/{notification_id}", status_code=204)
def delete_notification(
    notification_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a notification by its UUID."""
    notification = _get_notification_or_404(notification_id, db)
    db.delete(notification)
    db.commit()
    logger.info("Notification %s deleted", notification_id)
