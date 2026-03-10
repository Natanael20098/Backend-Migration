import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LoanPayment(Base):
    """
    Actual loan payment records — mirrors the loan_payments table.

    Status values: PENDING, PAID, LATE, MISSED, PARTIAL
    """

    __tablename__ = "loan_payments"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    loan_application_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    principal_amount: Mapped[float | None] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )
    interest_amount: Mapped[float | None] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )
    escrow_amount: Mapped[float | None] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )
    total_amount: Mapped[float | None] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )
    additional_principal: Mapped[float | None] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )
    late_fee: Mapped[float | None] = mapped_column(
        Numeric(precision=10, scale=2), nullable=True
    )
    payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    confirmation_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    borrower_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    loan_amount: Mapped[float | None] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
