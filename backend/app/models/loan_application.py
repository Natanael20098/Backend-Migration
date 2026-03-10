import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class LoanApplication(Base):
    """
    Loan application entity — minimal model to provide the loan_applications
    table that LoanPayment references via foreign key.
    Mirrors the core fields of the Java LoanApplication JPA entity.
    """

    __tablename__ = "loan_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    loan_number: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="SUBMITTED")
    loan_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    loan_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )
    interest_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=5, scale=3), nullable=True
    )
    loan_term_months: Mapped[int | None] = mapped_column(nullable=True)
    monthly_payment: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )
    down_payment: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=12, scale=2), nullable=True
    )
    property_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    borrower_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    borrower_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submitted_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
