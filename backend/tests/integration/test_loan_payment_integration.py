"""
Integration tests for LoanPayment endpoints.

These tests run against a real PostgreSQL database and require:
  - INTEGRATION_TESTS=1 environment variable (or --run-integration CLI flag)
  - A running PostgreSQL instance at DATABASE_URL

They are automatically skipped when PostgreSQL is not reachable.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

# Mark entire module as integration tests
pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _loan_app_id(pg_session) -> uuid.UUID:
    """Insert a minimal LoanApplication and return its id."""
    from app.models.loan_application import LoanApplication
    app_obj = LoanApplication(status="SUBMITTED")
    pg_session.add(app_obj)
    pg_session.commit()
    pg_session.refresh(app_obj)
    return app_obj.id


def _payment_payload(loan_app_id: uuid.UUID, **overrides) -> dict:
    base = {
        "loan_application_id": str(loan_app_id),
        "due_date": str(date.today()),
        "status": "PENDING",
        "total_amount": "1500.00",
        "principal_amount": "1200.00",
        "interest_amount": "300.00",
    }
    base.update(overrides)
    return base


def _create_payment(client: TestClient, loan_app_id: uuid.UUID, **overrides) -> dict:
    response = client.post("/api/loan-payments", json=_payment_payload(loan_app_id, **overrides))
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Integration: full CRUD lifecycle
# ---------------------------------------------------------------------------

class TestLoanPaymentCRUDIntegration:
    """Full CRUD lifecycle against real PostgreSQL."""

    def test_create_and_retrieve(self, pg_client: TestClient, pg_session):
        lid = _loan_app_id(pg_session)
        created = _create_payment(pg_client, lid, borrower_name="Integration User")
        fetched = pg_client.get(f"/api/loan-payments/{created['id']}").json()
        assert fetched["id"] == created["id"]
        assert fetched["borrower_name"] == "Integration User"

    def test_create_list_filter(self, pg_client: TestClient, pg_session):
        lid = _loan_app_id(pg_session)
        _create_payment(pg_client, lid, status="PAID")
        _create_payment(pg_client, lid, status="PENDING")
        data = pg_client.get(f"/api/loan-payments?loan_application_id={lid}").json()
        assert len(data) == 2

    def test_patch_status(self, pg_client: TestClient, pg_session):
        lid = _loan_app_id(pg_session)
        created = _create_payment(pg_client, lid, status="PENDING")
        updated = pg_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "PAID", "paid_date": str(date.today())},
        ).json()
        assert updated["status"] == "PAID"

    def test_delete(self, pg_client: TestClient, pg_session):
        lid = _loan_app_id(pg_session)
        created = _create_payment(pg_client, lid)
        pid = created["id"]
        response = pg_client.delete(f"/api/loan-payments/{pid}")
        assert response.status_code == 204
        get_resp = pg_client.get(f"/api/loan-payments/{pid}")
        assert get_resp.status_code == 404

    def test_payment_summary_aggregates_correctly(self, pg_client: TestClient, pg_session):
        lid = _loan_app_id(pg_session)
        _create_payment(pg_client, lid, status="PAID", total_amount="1000.00")
        _create_payment(pg_client, lid, status="PENDING", total_amount="800.00")
        _create_payment(pg_client, lid, status="LATE", total_amount="800.00", late_fee="25.00")

        data = pg_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert data["total_payments"] == 3
        assert data["paid_count"] == 1
        assert data["late_count"] == 1
        assert data["pending_count"] == 1
        assert float(data["total_paid"]) == 1000.0
        assert float(data["total_outstanding"]) == 1600.0
        assert float(data["total_late_fees"]) == 25.0

    def test_overdue_detection(self, pg_client: TestClient, pg_session):
        lid = _loan_app_id(pg_session)
        past_date = date.today() - timedelta(days=15)
        _create_payment(pg_client, lid, status="PENDING", due_date=str(past_date))
        data = pg_client.get("/api/loan-payments/overdue").json()
        overdue_ids = [p["id"] for p in data]
        # At least one overdue entry exists (could be more from other tests in the session)
        assert len(overdue_ids) >= 1

    def test_data_persists_after_commit(self, pg_client: TestClient, pg_session):
        """Verify that data actually persists in PostgreSQL (not just in-memory)."""
        lid = _loan_app_id(pg_session)
        created = _create_payment(pg_client, lid, confirmation_number="PG-PERSIST-001")

        # Fetch immediately
        fetched = pg_client.get(f"/api/loan-payments/{created['id']}").json()
        assert fetched["confirmation_number"] == "PG-PERSIST-001"
