"""
Unit tests for app/routers/loan_payments.py

Covers:
  - POST   /api/loan-payments                               (create)
  - GET    /api/loan-payments                               (list with filters)
  - GET    /api/loan-payments/overdue                       (overdue payments)
  - GET    /api/loan-payments/summary/{loan_application_id} (analytics)
  - GET    /api/loan-payments/{id}                          (get by id)
  - PUT    /api/loan-payments/{id}                          (full replace)
  - PATCH  /api/loan-payments/{id}                          (partial update)
  - DELETE /api/loan-payments/{id}                          (delete)

  Edge cases:
  - Invalid payloads → 422
  - Non-existent resource → 404
  - Status validation
  - Filter parameters
"""

import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _loan_app_id(db_session) -> uuid.UUID:
    """Insert a minimal LoanApplication row and return its id."""
    from app.models.loan_application import LoanApplication
    app_obj = LoanApplication(status="SUBMITTED")
    db_session.add(app_obj)
    db_session.commit()
    db_session.refresh(app_obj)
    return app_obj.id


def _payment_payload(loan_app_id: uuid.UUID, **overrides) -> dict:
    """Return a minimal valid LoanPaymentCreate payload."""
    base = {
        "loan_application_id": str(loan_app_id),
        "due_date": str(date.today()),
        "status": "PENDING",
        "total_amount": "1500.00",
    }
    base.update(overrides)
    return base


def _create_payment(client: TestClient, loan_app_id: uuid.UUID, **overrides) -> dict:
    """POST a loan payment and assert 201."""
    response = client.post("/api/loan-payments", json=_payment_payload(loan_app_id, **overrides))
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Model unit tests
# ---------------------------------------------------------------------------

class TestLoanPaymentModel:
    """ORM model has the expected table name and columns."""

    def test_tablename(self):
        from app.models.loan_payment import LoanPayment
        assert LoanPayment.__tablename__ == "loan_payments"

    def test_has_id(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "id")

    def test_has_loan_application_id(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "loan_application_id")

    def test_has_due_date(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "due_date")

    def test_has_status(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "status")

    def test_has_total_amount(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "total_amount")

    def test_has_created_at(self):
        from app.models.loan_payment import LoanPayment
        assert hasattr(LoanPayment, "created_at")

    def test_db_persistence(self, db_session):
        """LoanPayment can be persisted and retrieved."""
        from app.models.loan_application import LoanApplication
        from app.models.loan_payment import LoanPayment

        app_obj = LoanApplication(status="SUBMITTED")
        db_session.add(app_obj)
        db_session.commit()

        pmt = LoanPayment(
            loan_application_id=app_obj.id,
            due_date=date.today(),
            status="PENDING",
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)

        fetched = db_session.get(LoanPayment, pmt.id)
        assert fetched is not None
        assert fetched.status == "PENDING"


# ---------------------------------------------------------------------------
# Schema unit tests
# ---------------------------------------------------------------------------

class TestLoanPaymentSchemas:
    """Pydantic schemas validate and reject data correctly."""

    def test_create_schema_accepts_valid_payload(self):
        from app.schemas.loan_payment import LoanPaymentCreate
        loan_app_id = uuid.uuid4()
        schema = LoanPaymentCreate(loan_application_id=loan_app_id, due_date=date.today())
        assert schema.status == "PENDING"

    def test_create_schema_rejects_invalid_status(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises((ValidationError, ValueError)):
            LoanPaymentCreate(
                loan_application_id=uuid.uuid4(),
                due_date=date.today(),
                status="INVALID_STATUS",
            )

    def test_create_schema_rejects_negative_total_amount(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentCreate
        with pytest.raises(ValidationError):
            LoanPaymentCreate(
                loan_application_id=uuid.uuid4(),
                due_date=date.today(),
                total_amount=Decimal("-10.00"),
            )

    def test_create_schema_accepts_all_valid_statuses(self):
        from app.schemas.loan_payment import LoanPaymentCreate, VALID_STATUSES
        loan_app_id = uuid.uuid4()
        for status in VALID_STATUSES:
            schema = LoanPaymentCreate(
                loan_application_id=loan_app_id,
                due_date=date.today(),
                status=status,
            )
            assert schema.status == status

    def test_update_schema_accepts_partial_payload(self):
        from app.schemas.loan_payment import LoanPaymentUpdate
        schema = LoanPaymentUpdate(status="PAID")
        assert schema.status == "PAID"
        assert schema.due_date is None

    def test_update_schema_rejects_invalid_status(self):
        from pydantic import ValidationError
        from app.schemas.loan_payment import LoanPaymentUpdate
        with pytest.raises((ValidationError, ValueError)):
            LoanPaymentUpdate(status="BOGUS")

    def test_read_schema_from_orm(self, db_session):
        from app.models.loan_application import LoanApplication
        from app.models.loan_payment import LoanPayment
        from app.schemas.loan_payment import LoanPaymentRead

        app_obj = LoanApplication(status="SUBMITTED")
        db_session.add(app_obj)
        db_session.commit()

        pmt = LoanPayment(
            loan_application_id=app_obj.id,
            due_date=date.today(),
            status="PAID",
        )
        db_session.add(pmt)
        db_session.commit()
        db_session.refresh(pmt)

        schema = LoanPaymentRead.model_validate(pmt)
        assert schema.status == "PAID"
        assert schema.id == pmt.id


# ---------------------------------------------------------------------------
# POST /api/loan-payments
# ---------------------------------------------------------------------------

class TestCreateLoanPayment:
    """POST /api/loan-payments — create endpoint."""

    def test_returns_201(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        response = app_client.post("/api/loan-payments", json=_payment_payload(lid))
        assert response.status_code == 201

    def test_response_contains_id(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        data = _create_payment(app_client, lid)
        assert "id" in data
        uuid.UUID(data["id"])

    def test_response_default_status_pending(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        payload = {
            "loan_application_id": str(lid),
            "due_date": str(date.today()),
        }
        response = app_client.post("/api/loan-payments", json=payload)
        assert response.status_code == 201
        assert response.json()["status"] == "PENDING"

    def test_response_contains_created_at(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        data = _create_payment(app_client, lid)
        assert "created_at" in data
        datetime.fromisoformat(data["created_at"])

    def test_persists_all_fields(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        payload = {
            "loan_application_id": str(lid),
            "due_date": "2025-06-01",
            "paid_date": "2025-06-01",
            "payment_number": 3,
            "principal_amount": "800.00",
            "interest_amount": "200.00",
            "escrow_amount": "100.00",
            "total_amount": "1100.00",
            "additional_principal": "50.00",
            "status": "PAID",
            "late_fee": "0.00",
            "payment_method": "ACH",
            "confirmation_number": "CNF-123",
            "borrower_name": "John Doe",
            "loan_amount": "200000.00",
        }
        data = app_client.post("/api/loan-payments", json=payload).json()
        assert data["payment_number"] == 3
        assert data["status"] == "PAID"
        assert data["payment_method"] == "ACH"
        assert data["borrower_name"] == "John Doe"

    def test_missing_due_date_returns_422(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        payload = {"loan_application_id": str(lid), "status": "PENDING"}
        response = app_client.post("/api/loan-payments", json=payload)
        assert response.status_code == 422

    def test_missing_loan_application_id_returns_422(self, app_client: TestClient):
        payload = {"due_date": str(date.today()), "status": "PENDING"}
        response = app_client.post("/api/loan-payments", json=payload)
        assert response.status_code == 422

    def test_invalid_status_returns_422(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        payload = _payment_payload(lid, status="INVALID")
        response = app_client.post("/api/loan-payments", json=payload)
        assert response.status_code == 422

    def test_negative_total_amount_returns_422(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        payload = _payment_payload(lid, total_amount="-100.00")
        response = app_client.post("/api/loan-payments", json=payload)
        assert response.status_code == 422

    def test_response_content_type_is_json(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        response = app_client.post("/api/loan-payments", json=_payment_payload(lid))
        assert response.headers["content-type"].startswith("application/json")


# ---------------------------------------------------------------------------
# GET /api/loan-payments
# ---------------------------------------------------------------------------

class TestListLoanPayments:
    """GET /api/loan-payments — list endpoint."""

    def test_empty_list(self, app_client: TestClient):
        response = app_client.get("/api/loan-payments")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_created_payments(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        _create_payment(app_client, lid)
        _create_payment(app_client, lid)
        data = app_client.get("/api/loan-payments").json()
        assert len(data) == 2

    def test_filter_by_loan_application_id(self, app_client: TestClient, db_session):
        lid1 = _loan_app_id(db_session)
        lid2 = _loan_app_id(db_session)
        _create_payment(app_client, lid1)
        _create_payment(app_client, lid2)
        data = app_client.get(f"/api/loan-payments?loan_application_id={lid1}").json()
        assert len(data) == 1
        assert data[0]["loan_application_id"] == str(lid1)

    def test_filter_by_status(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        _create_payment(app_client, lid, status="PAID")
        _create_payment(app_client, lid, status="PENDING")
        data = app_client.get("/api/loan-payments?status=PAID").json()
        assert len(data) == 1
        assert data[0]["status"] == "PAID"

    def test_filter_by_due_date_range(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        today = date.today()
        past = today - timedelta(days=30)
        future = today + timedelta(days=30)
        _create_payment(app_client, lid, due_date=str(past))
        _create_payment(app_client, lid, due_date=str(today))
        _create_payment(app_client, lid, due_date=str(future))
        data = app_client.get(
            f"/api/loan-payments?due_date_from={today}&due_date_to={today}"
        ).json()
        assert len(data) == 1

    def test_returns_200(self, app_client: TestClient):
        response = app_client.get("/api/loan-payments")
        assert response.status_code == 200

    def test_response_is_list(self, app_client: TestClient):
        response = app_client.get("/api/loan-payments")
        assert isinstance(response.json(), list)

    def test_invalid_loan_application_id_returns_422(self, app_client: TestClient):
        response = app_client.get("/api/loan-payments?loan_application_id=not-a-uuid")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/loan-payments/overdue
# ---------------------------------------------------------------------------

class TestOverduePayments:
    """GET /api/loan-payments/overdue — overdue payments endpoint."""

    def test_returns_200(self, app_client: TestClient):
        response = app_client.get("/api/loan-payments/overdue")
        assert response.status_code == 200

    def test_empty_when_no_payments(self, app_client: TestClient):
        response = app_client.get("/api/loan-payments/overdue")
        assert response.json() == []

    def test_returns_overdue_pending(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        past = date.today() - timedelta(days=10)
        _create_payment(app_client, lid, due_date=str(past), status="PENDING")
        data = app_client.get("/api/loan-payments/overdue").json()
        assert len(data) == 1

    def test_excludes_paid_payments(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        past = date.today() - timedelta(days=10)
        _create_payment(app_client, lid, due_date=str(past), status="PAID")
        data = app_client.get("/api/loan-payments/overdue").json()
        assert len(data) == 0

    def test_excludes_future_pending(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        future = date.today() + timedelta(days=10)
        _create_payment(app_client, lid, due_date=str(future), status="PENDING")
        data = app_client.get("/api/loan-payments/overdue").json()
        assert len(data) == 0

    def test_custom_as_of_date(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        target_date = date.today() - timedelta(days=5)
        _create_payment(app_client, lid, due_date=str(target_date), status="PENDING")
        # Using a future as_of date should include this payment
        future_as_of = date.today() + timedelta(days=1)
        data = app_client.get(f"/api/loan-payments/overdue?as_of={future_as_of}").json()
        assert len(data) == 1


# ---------------------------------------------------------------------------
# GET /api/loan-payments/summary/{loan_application_id}
# ---------------------------------------------------------------------------

class TestPaymentSummary:
    """GET /api/loan-payments/summary/{loan_application_id} — analytics endpoint."""

    def test_returns_200(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        response = app_client.get(f"/api/loan-payments/summary/{lid}")
        assert response.status_code == 200

    def test_empty_summary_for_new_loan(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        data = app_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert data["total_payments"] == 0
        assert data["paid_count"] == 0
        assert float(data["total_paid"]) == 0.0

    def test_summary_counts_by_status(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        _create_payment(app_client, lid, status="PAID", total_amount="1000.00")
        _create_payment(app_client, lid, status="PAID", total_amount="500.00")
        _create_payment(app_client, lid, status="PENDING", total_amount="750.00")
        _create_payment(app_client, lid, status="LATE", total_amount="750.00")
        _create_payment(app_client, lid, status="MISSED", total_amount="750.00")

        data = app_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert data["total_payments"] == 5
        assert data["paid_count"] == 2
        assert data["late_count"] == 1
        assert data["missed_count"] == 1
        assert data["pending_count"] == 1
        assert float(data["total_paid"]) == 1500.0
        assert float(data["total_outstanding"]) == 1500.0

    def test_summary_contains_loan_application_id(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        data = app_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert data["loan_application_id"] == str(lid)

    def test_summary_invalid_uuid_returns_422(self, app_client: TestClient):
        response = app_client.get("/api/loan-payments/summary/not-a-uuid")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/loan-payments/{id}
# ---------------------------------------------------------------------------

class TestGetLoanPayment:
    """GET /api/loan-payments/{id} — single fetch endpoint."""

    def test_returns_200_for_existing(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        created = _create_payment(app_client, lid)
        response = app_client.get(f"/api/loan-payments/{created['id']}")
        assert response.status_code == 200

    def test_returns_correct_payment(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        created = _create_payment(app_client, lid, status="PAID")
        fetched = app_client.get(f"/api/loan-payments/{created['id']}").json()
        assert fetched["id"] == created["id"]
        assert fetched["status"] == "PAID"

    def test_returns_404_for_nonexistent(self, app_client: TestClient):
        response = app_client.get(f"/api/loan-payments/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_404_detail_message(self, app_client: TestClient):
        response = app_client.get(f"/api/loan-payments/{uuid.uuid4()}")
        assert "not found" in response.json()["detail"].lower()

    def test_invalid_uuid_returns_422(self, app_client: TestClient):
        response = app_client.get("/api/loan-payments/not-a-uuid")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PUT /api/loan-payments/{id}
# ---------------------------------------------------------------------------

class TestReplaceLoanPayment:
    """PUT /api/loan-payments/{id} — full replace endpoint."""

    def test_returns_200(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        created = _create_payment(app_client, lid, status="PENDING")
        payload = _payment_payload(lid, status="PAID")
        response = app_client.put(f"/api/loan-payments/{created['id']}", json=payload)
        assert response.status_code == 200

    def test_full_replace_updates_all_fields(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        created = _create_payment(app_client, lid, status="PENDING")
        payload = _payment_payload(lid, status="PAID", payment_method="WIRE")
        updated = app_client.put(
            f"/api/loan-payments/{created['id']}", json=payload
        ).json()
        assert updated["status"] == "PAID"
        assert updated["payment_method"] == "WIRE"

    def test_put_nonexistent_returns_404(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        response = app_client.put(
            f"/api/loan-payments/{uuid.uuid4()}", json=_payment_payload(lid)
        )
        assert response.status_code == 404

    def test_put_invalid_uuid_returns_422(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        response = app_client.put(
            "/api/loan-payments/bad-id", json=_payment_payload(lid)
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/loan-payments/{id}
# ---------------------------------------------------------------------------

class TestUpdateLoanPayment:
    """PATCH /api/loan-payments/{id} — partial update endpoint."""

    def test_returns_200(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        created = _create_payment(app_client, lid, status="PENDING")
        response = app_client.patch(
            f"/api/loan-payments/{created['id']}", json={"status": "PAID"}
        )
        assert response.status_code == 200

    def test_partial_update_changes_only_given_field(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        created = _create_payment(app_client, lid, status="PENDING", total_amount="1000.00")
        updated = app_client.patch(
            f"/api/loan-payments/{created['id']}", json={"status": "PAID"}
        ).json()
        assert updated["status"] == "PAID"
        assert float(updated["total_amount"]) == 1000.0

    def test_patch_paid_date(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        created = _create_payment(app_client, lid, status="PENDING")
        today = str(date.today())
        updated = app_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"paid_date": today, "status": "PAID"},
        ).json()
        assert updated["paid_date"] == today

    def test_patch_nonexistent_returns_404(self, app_client: TestClient):
        response = app_client.patch(
            f"/api/loan-payments/{uuid.uuid4()}", json={"status": "PAID"}
        )
        assert response.status_code == 404

    def test_patch_invalid_status_returns_422(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        created = _create_payment(app_client, lid)
        response = app_client.patch(
            f"/api/loan-payments/{created['id']}", json={"status": "BOGUS"}
        )
        assert response.status_code == 422

    def test_patch_invalid_uuid_returns_422(self, app_client: TestClient):
        response = app_client.patch("/api/loan-payments/bad-id", json={"status": "PAID"})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/loan-payments/{id}
# ---------------------------------------------------------------------------

class TestDeleteLoanPayment:
    """DELETE /api/loan-payments/{id} — delete endpoint."""

    def test_delete_returns_204(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        created = _create_payment(app_client, lid)
        response = app_client.delete(f"/api/loan-payments/{created['id']}")
        assert response.status_code == 204

    def test_delete_removes_payment(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        created = _create_payment(app_client, lid)
        pid = created["id"]
        app_client.delete(f"/api/loan-payments/{pid}")
        get_response = app_client.get(f"/api/loan-payments/{pid}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_returns_404(self, app_client: TestClient):
        response = app_client.delete(f"/api/loan-payments/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_delete_removes_only_target(self, app_client: TestClient, db_session):
        lid = _loan_app_id(db_session)
        p1 = _create_payment(app_client, lid)
        p2 = _create_payment(app_client, lid)
        app_client.delete(f"/api/loan-payments/{p2['id']}")
        remaining = app_client.get("/api/loan-payments").json()
        assert len(remaining) == 1
        assert remaining[0]["id"] == p1["id"]

    def test_delete_invalid_uuid_returns_422(self, app_client: TestClient):
        response = app_client.delete("/api/loan-payments/not-a-uuid")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

class TestLoanPaymentRouterRegistration:
    """LoanPayment router is mounted on the FastAPI app."""

    def test_post_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/loan-payments" in paths

    def test_get_by_id_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/loan-payments/{payment_id}" in paths

    def test_overdue_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/loan-payments/overdue" in paths

    def test_summary_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/loan-payments/summary/{loan_application_id}" in paths

    def test_delete_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/loan-payments/{payment_id}" in paths
