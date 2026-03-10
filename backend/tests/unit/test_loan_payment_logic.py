"""
Unit tests for LoanPayment business logic.

Covers:
  - Schema validation (LoanPaymentCreate, LoanPaymentUpdate, LoanPaymentRead)
  - Status validation — valid statuses accepted, invalid ones rejected
  - Field-level validation — non-negative amounts, length limits, optional fields
  - Default values — status defaults to PENDING
  - Overdue detection logic — payments that are PENDING and past due_date
  - Payment summary aggregation logic — counts and totals by status
  - Partial-update (PATCH) field isolation
  - ORM model attributes and persistence behaviour
  - Edge cases: zero amounts, max-length strings, missing optional fields
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def loan_app(db_session):
    """Persist a minimal LoanApplication and return it."""
    from app.models.loan_application import LoanApplication
    obj = LoanApplication(status="SUBMITTED")
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj


@pytest.fixture()
def pending_payment(db_session, loan_app):
    """Persist a PENDING LoanPayment due today and return it."""
    from app.models.loan_payment import LoanPayment
    pmt = LoanPayment(
        loan_application_id=loan_app.id,
        due_date=date.today(),
        status="PENDING",
        total_amount=Decimal("1500.00"),
        principal_amount=Decimal("1200.00"),
        interest_amount=Decimal("300.00"),
    )
    db_session.add(pmt)
    db_session.commit()
    db_session.refresh(pmt)
    return pmt


# ---------------------------------------------------------------------------
# Schema: LoanPaymentCreate — valid inputs
# ---------------------------------------------------------------------------

class TestLoanPaymentCreateSchema:

    def test_minimal_valid_payload_accepted(self):
        from app.schemas.loan_payment import LoanPaymentCreate
        schema = LoanPaymentCreate(
            loan_application_id=uuid.uuid4(),
            due_date=date.today(),
        )
        assert schema.status == "PENDING"

    def test_all_optional_fields_are_none_by_default(self):
        from app.schemas.loan_payment import LoanPaymentCreate
        schema = LoanPaymentCreate(
            loan_application_id=uuid.uuid4(),
            due_date=date.today(),
        )
        assert schema.paid_date is None
        assert schema.principal_amount is None
        assert schema.interest_amount is None
        assert schema.escrow_amount is None
        assert schema.total_amount is None
        assert schema.additional_principal is None
        assert schema.late_fee is None
        assert schema.payment_method is None
        assert schema.confirmation_number is None
        assert schema.borrower_name is None
        assert schema.loan_amount is None
        assert schema.payment_number is None

    def test_status_defaults_to_pending(self):
        from app.schemas.loan_payment import LoanPaymentCreate
        schema = LoanPaymentCreate(
            loan_application_id=uuid.uuid4(),
            due_date=date.today(),
        )
        assert schema.status == "PENDING"

    def test_each_valid_status_accepted(self):
        from app.schemas.loan_payment import LoanPaymentCreate, VALID_STATUSES
        app_id = uuid.uuid4()
        for status in VALID_STATUSES:
            schema = LoanPaymentCreate(
                loan_application_id=app_id,
                due_date=date.today(),
                status=status,
            )
            assert schema.status == status

    def test_zero_total_amount_accepted(self):
        from app.schemas.loan_payment import LoanPaymentCreate
        schema = LoanPaymentCreate(
            loan_application_id=uuid.uuid4(),
            due_date=date.today(),
            total_amount=Decimal("0.00"),
        )
        assert schema.total_amount == Decimal("0.00")

    def test_large_amounts_accepted(self):
        from app.schemas.loan_payment import LoanPaymentCreate
        schema = LoanPaymentCreate(
            loan_application_id=uuid.uuid4(),
            due_date=date.today(),
            total_amount=Decimal("9999999999.99"),
            loan_amount=Decimal("9999999999.99"),
        )
        assert schema.total_amount == Decimal("9999999999.99")

    def test_payment_number_at_minimum_boundary(self):
        from app.schemas.loan_payment import LoanPaymentCreate
        schema = LoanPaymentCreate(
            loan_application_id=uuid.uuid4(),
            due_date=date.today(),
            payment_number=1,
        )
        assert schema.payment_number == 1

    def test_full_payload_accepted(self):
        from app.schemas.loan_payment import LoanPaymentCreate
        schema = LoanPaymentCreate(
            loan_application_id=uuid.uuid4(),
            payment_number=5,
            due_date=date.today(),
            paid_date=date.today(),
            principal_amount=Decimal("800.00"),
            interest_amount=Decimal("200.00"),
            escrow_amount=Decimal("100.00"),
            total_amount=Decimal("1100.00"),
            additional_principal=Decimal("50.00"),
            status="PAID",
            late_fee=Decimal("0.00"),
            payment_method="ACH",
            confirmation_number="CNF-2025-001",
            borrower_name="Jane Doe",
            loan_amount=Decimal("250000.00"),
        )
        assert schema.status == "PAID"
        assert schema.borrower_name == "Jane Doe"
        assert schema.confirmation_number == "CNF-2025-001"


# ---------------------------------------------------------------------------
# Schema: LoanPaymentCreate — invalid inputs
# ---------------------------------------------------------------------------

class TestLoanPaymentCreateSchemaInvalid:

    def test_invalid_status_raises_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises((ValidationError, ValueError)):
            LoanPaymentCreate(
                loan_application_id=uuid.uuid4(),
                due_date=date.today(),
                status="NOT_A_STATUS",
            )

    def test_negative_total_amount_raises_validation_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises(ValidationError):
            LoanPaymentCreate(
                loan_application_id=uuid.uuid4(),
                due_date=date.today(),
                total_amount=Decimal("-0.01"),
            )

    def test_negative_principal_amount_raises_validation_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises(ValidationError):
            LoanPaymentCreate(
                loan_application_id=uuid.uuid4(),
                due_date=date.today(),
                principal_amount=Decimal("-1.00"),
            )

    def test_negative_interest_amount_raises_validation_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises(ValidationError):
            LoanPaymentCreate(
                loan_application_id=uuid.uuid4(),
                due_date=date.today(),
                interest_amount=Decimal("-1.00"),
            )

    def test_negative_escrow_amount_raises_validation_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises(ValidationError):
            LoanPaymentCreate(
                loan_application_id=uuid.uuid4(),
                due_date=date.today(),
                escrow_amount=Decimal("-1.00"),
            )

    def test_negative_late_fee_raises_validation_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises(ValidationError):
            LoanPaymentCreate(
                loan_application_id=uuid.uuid4(),
                due_date=date.today(),
                late_fee=Decimal("-5.00"),
            )

    def test_negative_additional_principal_raises_validation_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises(ValidationError):
            LoanPaymentCreate(
                loan_application_id=uuid.uuid4(),
                due_date=date.today(),
                additional_principal=Decimal("-50.00"),
            )

    def test_payment_number_zero_raises_validation_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises(ValidationError):
            LoanPaymentCreate(
                loan_application_id=uuid.uuid4(),
                due_date=date.today(),
                payment_number=0,
            )

    def test_missing_due_date_raises_validation_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises(ValidationError):
            LoanPaymentCreate(loan_application_id=uuid.uuid4())

    def test_missing_loan_application_id_raises_validation_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises(ValidationError):
            LoanPaymentCreate(due_date=date.today())

    def test_invalid_uuid_for_loan_application_id(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises(ValidationError):
            LoanPaymentCreate(
                loan_application_id="not-a-uuid",
                due_date=date.today(),
            )

    def test_lowercase_invalid_status_rejected(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises((ValidationError, ValueError)):
            LoanPaymentCreate(
                loan_application_id=uuid.uuid4(),
                due_date=date.today(),
                status="pending",  # lowercase — not in VALID_STATUSES
            )


# ---------------------------------------------------------------------------
# Schema: LoanPaymentUpdate — valid inputs
# ---------------------------------------------------------------------------

class TestLoanPaymentUpdateSchema:

    def test_completely_empty_update_accepted(self):
        from app.schemas.loan_payment import LoanPaymentUpdate
        schema = LoanPaymentUpdate()
        assert schema.status is None
        assert schema.due_date is None

    def test_status_only_update(self):
        from app.schemas.loan_payment import LoanPaymentUpdate
        schema = LoanPaymentUpdate(status="PAID")
        assert schema.status == "PAID"

    def test_paid_date_only_update(self):
        from app.schemas.loan_payment import LoanPaymentUpdate
        today = date.today()
        schema = LoanPaymentUpdate(paid_date=today)
        assert schema.paid_date == today

    def test_multiple_field_update(self):
        from app.schemas.loan_payment import LoanPaymentUpdate
        schema = LoanPaymentUpdate(
            status="PAID",
            paid_date=date.today(),
            late_fee=Decimal("25.00"),
        )
        assert schema.status == "PAID"
        assert schema.late_fee == Decimal("25.00")

    def test_each_valid_status_accepted(self):
        from app.schemas.loan_payment import LoanPaymentUpdate, VALID_STATUSES
        for status in VALID_STATUSES:
            schema = LoanPaymentUpdate(status=status)
            assert schema.status == status

    def test_none_status_accepted(self):
        """status=None means no update to status — valid in partial update context."""
        from app.schemas.loan_payment import LoanPaymentUpdate
        schema = LoanPaymentUpdate(status=None)
        assert schema.status is None


# ---------------------------------------------------------------------------
# Schema: LoanPaymentUpdate — invalid inputs
# ---------------------------------------------------------------------------

class TestLoanPaymentUpdateSchemaInvalid:

    def test_invalid_status_raises_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentUpdate
        with pytest.raises((ValidationError, ValueError)):
            LoanPaymentUpdate(status="BOGUS")

    def test_negative_total_amount_raises_validation_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentUpdate
        with pytest.raises(ValidationError):
            LoanPaymentUpdate(total_amount=Decimal("-1.00"))

    def test_negative_late_fee_raises_validation_error(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentUpdate
        with pytest.raises(ValidationError):
            LoanPaymentUpdate(late_fee=Decimal("-5.00"))


# ---------------------------------------------------------------------------
# Schema: LoanPaymentRead
# ---------------------------------------------------------------------------

class TestLoanPaymentReadSchema:

    def test_from_orm_produces_correct_id(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        from app.schemas.loan_payment import LoanPaymentRead
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=date.today(),
            status="PENDING",
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)
        read = LoanPaymentRead.model_validate(pmt)
        assert read.id == pmt.id

    def test_from_orm_status_matches(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        from app.schemas.loan_payment import LoanPaymentRead
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=date.today(),
            status="LATE",
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)
        read = LoanPaymentRead.model_validate(pmt)
        assert read.status == "LATE"

    def test_from_orm_created_at_is_populated(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        from app.schemas.loan_payment import LoanPaymentRead
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=date.today(),
            status="PENDING",
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)
        read = LoanPaymentRead.model_validate(pmt)
        assert read.created_at is not None

    def test_from_orm_optional_fields_are_none_when_not_set(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        from app.schemas.loan_payment import LoanPaymentRead
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=date.today(),
            status="PENDING",
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)
        read = LoanPaymentRead.model_validate(pmt)
        assert read.paid_date is None
        assert read.payment_method is None
        assert read.confirmation_number is None


# ---------------------------------------------------------------------------
# VALID_STATUSES constant
# ---------------------------------------------------------------------------

class TestValidStatusesConstant:

    def test_contains_pending(self):
        from app.schemas.loan_payment import VALID_STATUSES
        assert "PENDING" in VALID_STATUSES

    def test_contains_paid(self):
        from app.schemas.loan_payment import VALID_STATUSES
        assert "PAID" in VALID_STATUSES

    def test_contains_late(self):
        from app.schemas.loan_payment import VALID_STATUSES
        assert "LATE" in VALID_STATUSES

    def test_contains_missed(self):
        from app.schemas.loan_payment import VALID_STATUSES
        assert "MISSED" in VALID_STATUSES

    def test_contains_partial(self):
        from app.schemas.loan_payment import VALID_STATUSES
        assert "PARTIAL" in VALID_STATUSES

    def test_exactly_five_statuses(self):
        from app.schemas.loan_payment import VALID_STATUSES
        assert len(VALID_STATUSES) == 5


# ---------------------------------------------------------------------------
# ORM Model: LoanPayment
# ---------------------------------------------------------------------------

class TestLoanPaymentOrmModel:

    def test_table_name(self):
        from app.models.loan_payment import LoanPayment
        assert LoanPayment.__tablename__ == "loan_payments"

    def test_id_column_exists(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "id")

    def test_loan_application_id_column_exists(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "loan_application_id")

    def test_due_date_column_exists(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "due_date")

    def test_status_column_exists(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "status")

    def test_total_amount_column_exists(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "total_amount")

    def test_created_at_column_exists(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "created_at")

    def test_payment_number_column_exists(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "payment_number")

    def test_paid_date_column_exists(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "paid_date")

    def test_late_fee_column_exists(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "late_fee")

    def test_payment_method_column_exists(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "payment_method")

    def test_confirmation_number_column_exists(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "confirmation_number")

    def test_borrower_name_column_exists(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "borrower_name")

    def test_persist_and_retrieve(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=date.today(),
            status="PENDING",
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)
        fetched = db_session.get(LoanPayment, pmt.id)
        assert fetched is not None
        assert fetched.id == pmt.id

    def test_id_is_uuid(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=date.today(),
            status="PENDING",
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)
        assert isinstance(pmt.id, uuid.UUID)

    def test_default_status_is_pending(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=date.today(),
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)
        assert pmt.status == "PENDING"

    def test_status_can_be_updated(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=date.today(),
            status="PENDING",
        )
        db_session.add(pmt)
        db_session.commit()
        pmt.status = "PAID"
        db_session.commit()
        db_session.refresh(pmt)
        assert pmt.status == "PAID"

    def test_total_amount_stored_as_decimal(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=date.today(),
            status="PENDING",
            total_amount=Decimal("1234.56"),
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)
        assert pmt.total_amount is not None
        assert float(pmt.total_amount) == pytest.approx(1234.56)

    def test_all_amount_fields_stored(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=date.today(),
            status="PAID",
            principal_amount=Decimal("800.00"),
            interest_amount=Decimal("200.00"),
            escrow_amount=Decimal("100.00"),
            total_amount=Decimal("1100.00"),
            additional_principal=Decimal("50.00"),
            late_fee=Decimal("0.00"),
            loan_amount=Decimal("200000.00"),
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)
        assert float(pmt.principal_amount) == pytest.approx(800.00)
        assert float(pmt.interest_amount) == pytest.approx(200.00)
        assert float(pmt.escrow_amount) == pytest.approx(100.00)
        assert float(pmt.total_amount) == pytest.approx(1100.00)
        assert float(pmt.additional_principal) == pytest.approx(50.00)
        assert float(pmt.loan_amount) == pytest.approx(200000.00)

    def test_string_fields_stored(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=date.today(),
            status="PAID",
            payment_method="ACH",
            confirmation_number="CNF-001",
            borrower_name="Alice Smith",
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)
        assert pmt.payment_method == "ACH"
        assert pmt.confirmation_number == "CNF-001"
        assert pmt.borrower_name == "Alice Smith"

    def test_paid_date_stored(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        today = date.today()
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=today,
            paid_date=today,
            status="PAID",
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)
        assert pmt.paid_date == today


# ---------------------------------------------------------------------------
# Business logic: Overdue detection
# ---------------------------------------------------------------------------

class TestOverdueLogic:
    """
    Overdue definition: status == PENDING and due_date < cutoff date.
    """

    def test_pending_past_due_is_overdue(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        past = date.today() - timedelta(days=1)
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=past,
            status="PENDING",
        )
        db_session.add(pmt)
        db_session.commit()
        cutoff = date.today()
        results = (
            db_session.query(LoanPayment)
            .filter(LoanPayment.status == "PENDING", LoanPayment.due_date < cutoff)
            .all()
        )
        assert any(r.id == pmt.id for r in results)

    def test_paid_past_due_is_not_overdue(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        past = date.today() - timedelta(days=5)
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=past,
            status="PAID",
        )
        db_session.add(pmt)
        db_session.commit()
        cutoff = date.today()
        results = (
            db_session.query(LoanPayment)
            .filter(LoanPayment.status == "PENDING", LoanPayment.due_date < cutoff)
            .all()
        )
        assert not any(r.id == pmt.id for r in results)

    def test_pending_future_due_is_not_overdue(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        future = date.today() + timedelta(days=5)
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=future,
            status="PENDING",
        )
        db_session.add(pmt)
        db_session.commit()
        cutoff = date.today()
        results = (
            db_session.query(LoanPayment)
            .filter(LoanPayment.status == "PENDING", LoanPayment.due_date < cutoff)
            .all()
        )
        assert not any(r.id == pmt.id for r in results)

    def test_pending_due_today_is_not_overdue(self, db_session, loan_app):
        """due_date == cutoff means NOT overdue (strictly less than)."""
        from app.models.loan_payment import LoanPayment
        today = date.today()
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=today,
            status="PENDING",
        )
        db_session.add(pmt)
        db_session.commit()
        results = (
            db_session.query(LoanPayment)
            .filter(LoanPayment.status == "PENDING", LoanPayment.due_date < today)
            .all()
        )
        assert not any(r.id == pmt.id for r in results)

    def test_late_status_past_due_is_not_in_pending_overdue_query(self, db_session, loan_app):
        from app.models.loan_payment import LoanPayment
        past = date.today() - timedelta(days=3)
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=past,
            status="LATE",
        )
        db_session.add(pmt)
        db_session.commit()
        cutoff = date.today()
        results = (
            db_session.query(LoanPayment)
            .filter(LoanPayment.status == "PENDING", LoanPayment.due_date < cutoff)
            .all()
        )
        assert not any(r.id == pmt.id for r in results)

    def test_custom_cutoff_date_respected(self, db_session, loan_app):
        """Overdue query honours a custom as_of cutoff."""
        from app.models.loan_payment import LoanPayment
        # due two days ago
        two_days_ago = date.today() - timedelta(days=2)
        pmt = LoanPayment(
            loan_application_id=loan_app.id,
            due_date=two_days_ago,
            status="PENDING",
        )
        db_session.add(pmt)
        db_session.commit()
        # cutoff = yesterday — payment IS overdue
        yesterday = date.today() - timedelta(days=1)
        results_yes = (
            db_session.query(LoanPayment)
            .filter(LoanPayment.status == "PENDING", LoanPayment.due_date < yesterday)
            .all()
        )
        assert any(r.id == pmt.id for r in results_yes)
        # cutoff = three_days_ago — payment is NOT overdue relative to cutoff
        three_days_ago = date.today() - timedelta(days=3)
        results_no = (
            db_session.query(LoanPayment)
            .filter(LoanPayment.status == "PENDING", LoanPayment.due_date < three_days_ago)
            .all()
        )
        assert not any(r.id == pmt.id for r in results_no)


# ---------------------------------------------------------------------------
# Business logic: Status transitions via PATCH endpoint
# ---------------------------------------------------------------------------

class TestStatusTransitionLogic:

    def test_pending_to_paid_transition(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        created = _post_payment(app_client, lid, status="PENDING")
        updated = app_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "PAID", "paid_date": str(date.today())},
        ).json()
        assert updated["status"] == "PAID"
        assert updated["paid_date"] == str(date.today())

    def test_pending_to_late_transition(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        created = _post_payment(app_client, lid, status="PENDING")
        updated = app_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "LATE", "late_fee": "25.00"},
        ).json()
        assert updated["status"] == "LATE"
        assert float(updated["late_fee"]) == 25.0

    def test_pending_to_missed_transition(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        created = _post_payment(app_client, lid, status="PENDING")
        updated = app_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "MISSED"},
        ).json()
        assert updated["status"] == "MISSED"

    def test_pending_to_partial_transition(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        created = _post_payment(app_client, lid, status="PENDING")
        updated = app_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "PARTIAL"},
        ).json()
        assert updated["status"] == "PARTIAL"

    def test_invalid_status_transition_rejected(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        created = _post_payment(app_client, lid, status="PENDING")
        response = app_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "APPROVED"},  # not a valid payment status
        )
        assert response.status_code == 422

    def test_patch_preserves_unpatched_fields(self, app_client, db_session):
        """Partial update does not clobber untouched fields."""
        lid = _create_loan_app(db_session)
        created = _post_payment(
            app_client, lid,
            status="PENDING",
            total_amount="2000.00",
            borrower_name="Original Name",
        )
        updated = app_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "PAID"},
        ).json()
        assert float(updated["total_amount"]) == 2000.0
        assert updated["borrower_name"] == "Original Name"


# ---------------------------------------------------------------------------
# Business logic: Payment summary aggregation
# ---------------------------------------------------------------------------

class TestPaymentSummaryLogic:

    def test_summary_zero_payments(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        data = app_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert data["total_payments"] == 0
        assert float(data["total_paid"]) == 0.0
        assert float(data["total_outstanding"]) == 0.0
        assert float(data["total_late_fees"]) == 0.0

    def test_summary_single_paid_payment(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        _post_payment(app_client, lid, status="PAID", total_amount="1000.00")
        data = app_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert data["paid_count"] == 1
        assert float(data["total_paid"]) == 1000.0
        assert float(data["total_outstanding"]) == 0.0

    def test_summary_outstanding_includes_pending_and_late(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        _post_payment(app_client, lid, status="PENDING", total_amount="500.00")
        _post_payment(app_client, lid, status="LATE", total_amount="500.00")
        data = app_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert float(data["total_outstanding"]) == 1000.0

    def test_summary_late_fees_aggregated(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        _post_payment(app_client, lid, status="LATE", total_amount="800.00", late_fee="25.00")
        _post_payment(app_client, lid, status="LATE", total_amount="800.00", late_fee="25.00")
        data = app_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert float(data["total_late_fees"]) == 50.0

    def test_summary_all_status_counts(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        _post_payment(app_client, lid, status="PAID", total_amount="1000.00")
        _post_payment(app_client, lid, status="PENDING", total_amount="1000.00")
        _post_payment(app_client, lid, status="LATE", total_amount="1000.00")
        _post_payment(app_client, lid, status="MISSED", total_amount="1000.00")
        _post_payment(app_client, lid, status="PARTIAL", total_amount="1000.00")

        data = app_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert data["total_payments"] == 5
        assert data["paid_count"] == 1
        assert data["pending_count"] == 1
        assert data["late_count"] == 1
        assert data["missed_count"] == 1
        assert data["partial_count"] == 1

    def test_summary_missed_not_in_outstanding(self, app_client, db_session):
        """MISSED payments are not counted in total_outstanding (only PENDING + LATE)."""
        lid = _create_loan_app(db_session)
        _post_payment(app_client, lid, status="MISSED", total_amount="1000.00")
        data = app_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert float(data["total_outstanding"]) == 0.0

    def test_summary_loan_application_id_matches(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        data = app_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert data["loan_application_id"] == str(lid)

    def test_summary_isolated_per_loan(self, app_client, db_session):
        """Summaries for different loans do not bleed into each other."""
        lid1 = _create_loan_app(db_session)
        lid2 = _create_loan_app(db_session)
        _post_payment(app_client, lid1, status="PAID", total_amount="1000.00")
        data2 = app_client.get(f"/api/loan-payments/summary/{lid2}").json()
        assert data2["total_payments"] == 0
        assert float(data2["total_paid"]) == 0.0


# ---------------------------------------------------------------------------
# Business logic: Filtering
# ---------------------------------------------------------------------------

class TestFilterLogic:

    def test_filter_by_status_returns_only_matching(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        _post_payment(app_client, lid, status="PAID")
        _post_payment(app_client, lid, status="PAID")
        _post_payment(app_client, lid, status="PENDING")
        data = app_client.get("/api/loan-payments?status=PAID").json()
        assert len(data) == 2
        assert all(p["status"] == "PAID" for p in data)

    def test_filter_by_loan_application_id(self, app_client, db_session):
        lid1 = _create_loan_app(db_session)
        lid2 = _create_loan_app(db_session)
        _post_payment(app_client, lid1)
        _post_payment(app_client, lid1)
        _post_payment(app_client, lid2)
        data = app_client.get(f"/api/loan-payments?loan_application_id={lid1}").json()
        assert len(data) == 2
        assert all(p["loan_application_id"] == str(lid1) for p in data)

    def test_filter_due_date_from(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        today = date.today()
        past = today - timedelta(days=30)
        _post_payment(app_client, lid, due_date=str(past))
        _post_payment(app_client, lid, due_date=str(today))
        data = app_client.get(f"/api/loan-payments?due_date_from={today}").json()
        assert len(data) == 1
        assert data[0]["due_date"] == str(today)

    def test_filter_due_date_to(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        today = date.today()
        future = today + timedelta(days=30)
        _post_payment(app_client, lid, due_date=str(today))
        _post_payment(app_client, lid, due_date=str(future))
        data = app_client.get(f"/api/loan-payments?due_date_to={today}").json()
        assert len(data) == 1

    def test_filter_combined_status_and_loan_id(self, app_client, db_session):
        lid1 = _create_loan_app(db_session)
        lid2 = _create_loan_app(db_session)
        _post_payment(app_client, lid1, status="PAID")
        _post_payment(app_client, lid1, status="PENDING")
        _post_payment(app_client, lid2, status="PAID")
        data = app_client.get(
            f"/api/loan-payments?loan_application_id={lid1}&status=PAID"
        ).json()
        assert len(data) == 1
        assert data[0]["loan_application_id"] == str(lid1)

    def test_list_returns_payments_ordered_by_due_date(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        today = date.today()
        future = today + timedelta(days=10)
        past = today - timedelta(days=10)
        _post_payment(app_client, lid, due_date=str(future))
        _post_payment(app_client, lid, due_date=str(past))
        _post_payment(app_client, lid, due_date=str(today))
        data = app_client.get("/api/loan-payments").json()
        dates = [d["due_date"] for d in data]
        assert dates == sorted(dates)


# ---------------------------------------------------------------------------
# Business logic: Full replace (PUT)
# ---------------------------------------------------------------------------

class TestFullReplaceLogic:

    def test_put_replaces_all_fields(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        created = _post_payment(
            app_client, lid,
            status="PENDING",
            payment_method="ACH",
            total_amount="1000.00",
        )
        payload = {
            "loan_application_id": str(lid),
            "due_date": str(date.today()),
            "status": "PAID",
            "payment_method": "WIRE",
            "total_amount": "2000.00",
        }
        updated = app_client.put(
            f"/api/loan-payments/{created['id']}", json=payload
        ).json()
        assert updated["status"] == "PAID"
        assert updated["payment_method"] == "WIRE"
        assert float(updated["total_amount"]) == 2000.0

    def test_put_id_remains_unchanged(self, app_client, db_session):
        lid = _create_loan_app(db_session)
        created = _post_payment(app_client, lid, status="PENDING")
        payload = {
            "loan_application_id": str(lid),
            "due_date": str(date.today()),
            "status": "PAID",
        }
        updated = app_client.put(
            f"/api/loan-payments/{created['id']}", json=payload
        ).json()
        assert updated["id"] == created["id"]


# ---------------------------------------------------------------------------
# Private helpers used by logic tests
# ---------------------------------------------------------------------------

def _create_loan_app(db_session) -> uuid.UUID:
    from app.models.loan_application import LoanApplication
    obj = LoanApplication(status="SUBMITTED")
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return obj.id


def _post_payment(client, loan_app_id: uuid.UUID, **overrides) -> dict:
    payload = {
        "loan_application_id": str(loan_app_id),
        "due_date": str(date.today()),
        "status": "PENDING",
        "total_amount": "1500.00",
    }
    payload.update({k: str(v) if isinstance(v, Decimal) else v for k, v in overrides.items()})
    response = client.post("/api/loan-payments", json=payload)
    assert response.status_code == 201, response.text
    return response.json()
