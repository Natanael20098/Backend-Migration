import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


VALID_STATUSES = {"PENDING", "PAID", "LATE", "MISSED", "PARTIAL"}


class LoanPaymentCreate(BaseModel):
    """Schema for creating a new loan payment record."""

    loan_application_id: uuid.UUID
    payment_number: Optional[int] = Field(default=None, ge=1)
    due_date: date
    paid_date: Optional[date] = None
    principal_amount: Optional[Decimal] = Field(default=None, ge=0)
    interest_amount: Optional[Decimal] = Field(default=None, ge=0)
    escrow_amount: Optional[Decimal] = Field(default=None, ge=0)
    total_amount: Optional[Decimal] = Field(default=None, ge=0)
    additional_principal: Optional[Decimal] = Field(default=None, ge=0)
    status: str = Field(default="PENDING", max_length=20)
    late_fee: Optional[Decimal] = Field(default=None, ge=0)
    payment_method: Optional[str] = Field(default=None, max_length=50)
    confirmation_number: Optional[str] = Field(default=None, max_length=100)
    borrower_name: Optional[str] = Field(default=None, max_length=255)
    loan_amount: Optional[Decimal] = Field(default=None, ge=0)

    def model_post_init(self, __context) -> None:  # noqa: ANN001
        if self.status not in VALID_STATUSES:
            from pydantic import ValidationError
            raise ValueError(
                f"status must be one of {sorted(VALID_STATUSES)}, got '{self.status}'"
            )


class LoanPaymentUpdate(BaseModel):
    """Schema for updating an existing loan payment record (all fields optional)."""

    payment_number: Optional[int] = Field(default=None, ge=1)
    due_date: Optional[date] = None
    paid_date: Optional[date] = None
    principal_amount: Optional[Decimal] = Field(default=None, ge=0)
    interest_amount: Optional[Decimal] = Field(default=None, ge=0)
    escrow_amount: Optional[Decimal] = Field(default=None, ge=0)
    total_amount: Optional[Decimal] = Field(default=None, ge=0)
    additional_principal: Optional[Decimal] = Field(default=None, ge=0)
    status: Optional[str] = Field(default=None, max_length=20)
    late_fee: Optional[Decimal] = Field(default=None, ge=0)
    payment_method: Optional[str] = Field(default=None, max_length=50)
    confirmation_number: Optional[str] = Field(default=None, max_length=100)
    borrower_name: Optional[str] = Field(default=None, max_length=255)
    loan_amount: Optional[Decimal] = Field(default=None, ge=0)

    def model_post_init(self, __context) -> None:  # noqa: ANN001
        if self.status is not None and self.status not in VALID_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(VALID_STATUSES)}, got '{self.status}'"
            )


class LoanPaymentRead(BaseModel):
    """Schema for reading a loan payment record."""

    id: uuid.UUID
    loan_application_id: uuid.UUID
    payment_number: Optional[int]
    due_date: date
    paid_date: Optional[date]
    principal_amount: Optional[Decimal]
    interest_amount: Optional[Decimal]
    escrow_amount: Optional[Decimal]
    total_amount: Optional[Decimal]
    additional_principal: Optional[Decimal]
    status: str
    late_fee: Optional[Decimal]
    payment_method: Optional[str]
    confirmation_number: Optional[str]
    borrower_name: Optional[str]
    loan_amount: Optional[Decimal]
    created_at: datetime

    model_config = {"from_attributes": True}


class PaymentSummary(BaseModel):
    """Aggregated payment summary for a loan application."""

    loan_application_id: uuid.UUID
    total_payments: int
    paid_count: int
    late_count: int
    missed_count: int
    pending_count: int
    partial_count: int
    total_paid: Decimal
    total_outstanding: Decimal
    total_late_fees: Decimal
