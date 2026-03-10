from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import check_database_connection
from app.deps import get_db
from app.models.health_check import HealthCheck

router = APIRouter(tags=["health"])


@router.get("/health", status_code=200)
def health_check(db: Annotated[Session, Depends(get_db)]) -> dict:
    """
    Health check endpoint.

    Returns HTTP 200 with:
    - 'status': 'ok'
    - 'database': 'ok' | 'unavailable'
    - 'last_checked': ISO timestamp of the most recent health_check row
    """
    db_ok = check_database_connection()
    db_status = "ok" if db_ok else "unavailable"

    last_checked = None
    if db_ok:
        # Write a record (CREATE) then read it back (READ) — verifies basic CRUD
        entry = HealthCheck(status="ok")
        db.add(entry)
        db.commit()
        db.refresh(entry)
        last_checked = entry.checked_at.isoformat()

    return {
        "status": "ok",
        "database": db_status,
        "last_checked": last_checked,
    }
