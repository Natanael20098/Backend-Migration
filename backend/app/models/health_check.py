from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class HealthCheck(Base):
    """
    Sample table used to verify basic CRUD operations against PostgreSQL.
    Created automatically on startup when the database is available.
    """

    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ok")
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
