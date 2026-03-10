"""
LoanPayment API endpoints.

Endpoints:
  POST   /api/loan-payments                              — create a payment record
  GET    /api/loan-payments                              — list payments (filterable)
  GET    /api/loan-payments/{id}                         — get a single payment
  PUT    /api/loan-payments/{id}                         — full update of a payment
  PATCH  /api/loan-payments/{id}                         — partial update of a payment
  DELETE /api/loan-payments/{id}                         — delete a payment
  GET    /api/loan-payments/summary/{loan_application_id} — payment summary / analytics
  GET    /api/loan-payments/overdue                      — list overdue payments
"""

import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.deps import get_db
from app.models.loan_payment import LoanPayment
from app.schemas.loan_payment import (
    LoanPaymentCreate,
    LoanPaymentRead,
    LoanPaymentUpdate,
    PaymentSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/loan-payments", tags=["loan-payments"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_or_404(payment_id: uuid.UUID, db: Session) -> LoanPayment:
    """Fetch a LoanPayment by PK or raise HTTP 404."""
    obj = db.get(LoanPayment, payment_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="LoanPayment not found")
    return obj


# ---------------------------------------------------------------------------
# POST /api/loan-payments
# ---------------------------------------------------------------------------

@router.post("", response_model=LoanPaymentRead, status_code=201)
def create_loan_payment(
    payload: LoanPaymentCreate,
    db: Annotated[Session, Depends(get_db)],
) -> LoanPayment:
    """Create a new loan payment record."""
    payment = LoanPayment(
        loan_application_id=payload.loan_application_id,
        payment_number=payload.payment_number,
        due_date=payload.due_date,
        paid_date=payload.paid_date,
        principal_amount=payload.principal_amount,
        interest_amount=payload.interest_amount,
        escrow_amount=payload.escrow_amount,
        total_amount=payload.total_amount,
        additional_principal=payload.additional_principal,
        status=payload.status,
        late_fee=payload.late_fee,
        payment_method=payload.payment_method,
        confirmation_number=payload.confirmation_number,
        borrower_name=payload.borrower_name,
        loan_amount=payload.loan_amount,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    logger.info(
        "LoanPayment created: id=%s loan_application_id=%s status=%s",
        payment.id,
        payment.loan_application_id,
        payment.status,
    )
    return payment


# ---------------------------------------------------------------------------
# GET /api/loan-payments
# ---------------------------------------------------------------------------

@router.get("", response_model=list[LoanPaymentRead])
def list_loan_payments(
    db: Annotated[Session, Depends(get_db)],
    loan_application_id: Optional[uuid.UUID] = Query(default=None),
    status: Optional[str] = Query(default=None),
    due_date_from: Optional[date] = Query(default=None),
    due_date_to: Optional[date] = Query(default=None),
) -> list[LoanPayment]:
    """
    List loan payments with optional filters:
    - loan_application_id
    - status (PENDING | PAID | LATE | MISSED | PARTIAL)
    - due_date_from / due_date_to (date range)
    """
    query = db.query(LoanPayment)
    if loan_application_id is not None:
        query = query.filter(LoanPayment.loan_application_id == loan_application_id)
    if status is not None:
        query = query.filter(LoanPayment.status == status)
    if due_date_from is not None:
        query = query.filter(LoanPayment.due_date >= due_date_from)
    if due_date_to is not None:
        query = query.filter(LoanPayment.due_date <= due_date_to)
    results = query.order_by(LoanPayment.due_date.asc()).all()
    logger.info(
        "Listed %d loan payments (loan_application_id=%s, status=%s)",
        len(results),
        loan_application_id,
        status,
    )
    return results


# ---------------------------------------------------------------------------
# GET /api/loan-payments/overdue
# ---------------------------------------------------------------------------

@router.get("/overdue", response_model=list[LoanPaymentRead])
def list_overdue_payments(
    db: Annotated[Session, Depends(get_db)],
    as_of: Optional[date] = Query(default=None),
) -> list[LoanPayment]:
    """
    Return payments that are PENDING and whose due_date is in the past.
    Business logic: overdue = status PENDING and due_date < today (or as_of date).
    """
    cutoff = as_of if as_of is not None else date.today()
    results = (
        db.query(LoanPayment)
        .filter(LoanPayment.status == "PENDING", LoanPayment.due_date < cutoff)
        .order_by(LoanPayment.due_date.asc())
        .all()
    )
    logger.info("Found %d overdue payments (as_of=%s)", len(results), cutoff)
    return results


# ---------------------------------------------------------------------------
# GET /api/loan-payments/summary/{loan_application_id}
# ---------------------------------------------------------------------------

@router.get("/summary/{loan_application_id}", response_model=PaymentSummary)
def get_payment_summary(
    loan_application_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> PaymentSummary:
    """
    Return aggregated payment analytics for a specific loan application.
    Equivalent to the native summary query from LoanPaymentRepository.
    """
    row = (
        db.query(
            func.count().label("total_payments"),
            func.count(
                case((LoanPayment.status == "PAID", 1))
            ).label("paid_count"),
            func.count(
                case((LoanPayment.status == "LATE", 1))
            ).label("late_count"),
            func.count(
                case((LoanPayment.status == "MISSED", 1))
            ).label("missed_count"),
            func.count(
                case((LoanPayment.status == "PENDING", 1))
            ).label("pending_count"),
            func.count(
                case((LoanPayment.status == "PARTIAL", 1))
            ).label("partial_count"),
            func.coalesce(
                func.sum(
                    case((LoanPayment.status == "PAID", LoanPayment.total_amount))
                ),
                Decimal("0"),
            ).label("total_paid"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            LoanPayment.status.in_(["PENDING", "LATE"]),
                            LoanPayment.total_amount,
                        )
                    )
                ),
                Decimal("0"),
            ).label("total_outstanding"),
            func.coalesce(
                func.sum(LoanPayment.late_fee), Decimal("0")
            ).label("total_late_fees"),
        )
        .filter(LoanPayment.loan_application_id == loan_application_id)
        .one()
    )

    return PaymentSummary(
        loan_application_id=loan_application_id,
        total_payments=row.total_payments,
        paid_count=row.paid_count,
        late_count=row.late_count,
        missed_count=row.missed_count,
        pending_count=row.pending_count,
        partial_count=row.partial_count,
        total_paid=Decimal(str(row.total_paid)),
        total_outstanding=Decimal(str(row.total_outstanding)),
        total_late_fees=Decimal(str(row.total_late_fees)),
    )


# ---------------------------------------------------------------------------
# GET /api/loan-payments/{id}
# ---------------------------------------------------------------------------

@router.get("/{payment_id}", response_model=LoanPaymentRead)
def get_loan_payment(
    payment_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> LoanPayment:
    """Return a single loan payment by its UUID."""
    return _get_or_404(payment_id, db)


# ---------------------------------------------------------------------------
# PUT /api/loan-payments/{id}
# ---------------------------------------------------------------------------

@router.put("/{payment_id}", response_model=LoanPaymentRead)
def replace_loan_payment(
    payment_id: uuid.UUID,
    payload: LoanPaymentCreate,
    db: Annotated[Session, Depends(get_db)],
) -> LoanPayment:
    """Full replacement update of a loan payment record."""
    payment = _get_or_404(payment_id, db)
    payment.loan_application_id = payload.loan_application_id
    payment.payment_number = payload.payment_number
    payment.due_date = payload.due_date
    payment.paid_date = payload.paid_date
    payment.principal_amount = payload.principal_amount
    payment.interest_amount = payload.interest_amount
    payment.escrow_amount = payload.escrow_amount
    payment.total_amount = payload.total_amount
    payment.additional_principal = payload.additional_principal
    payment.status = payload.status
    payment.late_fee = payload.late_fee
    payment.payment_method = payload.payment_method
    payment.confirmation_number = payload.confirmation_number
    payment.borrower_name = payload.borrower_name
    payment.loan_amount = payload.loan_amount
    db.commit()
    db.refresh(payment)
    logger.info("LoanPayment %s replaced (status=%s)", payment_id, payment.status)
    return payment


# ---------------------------------------------------------------------------
# PATCH /api/loan-payments/{id}
# ---------------------------------------------------------------------------

@router.patch("/{payment_id}", response_model=LoanPaymentRead)
def update_loan_payment(
    payment_id: uuid.UUID,
    payload: LoanPaymentUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> LoanPayment:
    """Partial update of a loan payment record — only supplied fields are changed."""
    payment = _get_or_404(payment_id, db)
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(payment, field, value)
    db.commit()
    db.refresh(payment)
    logger.info("LoanPayment %s partially updated: fields=%s", payment_id, list(update_data))
    return payment


# ---------------------------------------------------------------------------
# DELETE /api/loan-payments/{id}
# ---------------------------------------------------------------------------

@router.delete("/{payment_id}", status_code=204)
def delete_loan_payment(
    payment_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
) -> None:
    """Delete a loan payment by its UUID."""
    payment = _get_or_404(payment_id, db)
    db.delete(payment)
    db.commit()
    logger.info("LoanPayment %s deleted", payment_id)
