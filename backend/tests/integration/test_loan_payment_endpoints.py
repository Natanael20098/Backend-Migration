"""
Integration tests for LoanPayment endpoints.

These tests run against a real PostgreSQL database.  They are automatically
skipped when PostgreSQL is not reachable.

Requirements:
  - INTEGRATION_TESTS=1 environment variable  (or --run-integration CLI flag)
  - A running PostgreSQL instance at DATABASE_URL
    (default: postgresql://chiron:chiron@localhost:5432/chiron)
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

# Mark the entire module as integration
pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_loan_app(pg_session) -> uuid.UUID:
    """Insert a minimal LoanApplication row and return its UUID."""
    from app.models.loan_application import LoanApplication
    obj = LoanApplication(status="SUBMITTED")
    pg_session.add(obj)
    pg_session.commit()
    pg_session.refresh(obj)
    return obj.id


def _payment_payload(loan_app_id: uuid.UUID, **overrides) -> dict:
    """Build a minimal valid POST body for /api/loan-payments."""
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
    """POST a payment and assert HTTP 201."""
    resp = client.post("/api/loan-payments", json=_payment_payload(loan_app_id, **overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# CREATE — POST /api/loan-payments
# ---------------------------------------------------------------------------

class TestCreatePaymentIntegration:

    def test_create_returns_201(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        resp = pg_client.post("/api/loan-payments", json=_payment_payload(lid))
        assert resp.status_code == 201

    def test_created_response_has_id(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        data = _create_payment(pg_client, lid)
        assert "id" in data
        uuid.UUID(data["id"])  # must be a valid UUID

    def test_created_response_has_created_at(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        data = _create_payment(pg_client, lid)
        assert "created_at" in data
        assert data["created_at"] is not None

    def test_create_stores_all_fields(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        payload = _payment_payload(
            lid,
            payment_number=7,
            paid_date=str(date.today()),
            principal_amount="900.00",
            interest_amount="250.00",
            escrow_amount="150.00",
            total_amount="1300.00",
            additional_principal="100.00",
            status="PAID",
            late_fee="0.00",
            payment_method="WIRE",
            confirmation_number="WIRE-2025-001",
            borrower_name="Integration Tester",
            loan_amount="350000.00",
        )
        data = pg_client.post("/api/loan-payments", json=payload).json()
        assert data["payment_number"] == 7
        assert data["status"] == "PAID"
        assert data["payment_method"] == "WIRE"
        assert data["confirmation_number"] == "WIRE-2025-001"
        assert data["borrower_name"] == "Integration Tester"

    def test_default_status_is_pending(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        payload = {"loan_application_id": str(lid), "due_date": str(date.today())}
        data = pg_client.post("/api/loan-payments", json=payload).json()
        assert data["status"] == "PENDING"

    def test_create_missing_due_date_returns_422(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        payload = {"loan_application_id": str(lid), "status": "PENDING"}
        resp = pg_client.post("/api/loan-payments", json=payload)
        assert resp.status_code == 422

    def test_create_missing_loan_id_returns_422(self, pg_client):
        payload = {"due_date": str(date.today()), "status": "PENDING"}
        resp = pg_client.post("/api/loan-payments", json=payload)
        assert resp.status_code == 422

    def test_create_invalid_status_returns_422(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        resp = pg_client.post(
            "/api/loan-payments", json=_payment_payload(lid, status="INVALID")
        )
        assert resp.status_code == 422

    def test_create_negative_amount_returns_422(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        resp = pg_client.post(
            "/api/loan-payments", json=_payment_payload(lid, total_amount="-1.00")
        )
        assert resp.status_code == 422

    def test_content_type_is_json(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        resp = pg_client.post("/api/loan-payments", json=_payment_payload(lid))
        assert resp.headers["content-type"].startswith("application/json")


# ---------------------------------------------------------------------------
# READ — GET /api/loan-payments/{id}
# ---------------------------------------------------------------------------

class TestGetPaymentIntegration:

    def test_get_existing_returns_200(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid)
        resp = pg_client.get(f"/api/loan-payments/{created['id']}")
        assert resp.status_code == 200

    def test_get_returns_correct_data(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid, borrower_name="Persist Test")
        fetched = pg_client.get(f"/api/loan-payments/{created['id']}").json()
        assert fetched["id"] == created["id"]
        assert fetched["borrower_name"] == "Persist Test"

    def test_get_nonexistent_returns_404(self, pg_client):
        resp = pg_client.get(f"/api/loan-payments/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_get_404_detail_message(self, pg_client):
        resp = pg_client.get(f"/api/loan-payments/{uuid.uuid4()}")
        assert "not found" in resp.json()["detail"].lower()

    def test_get_invalid_uuid_returns_422(self, pg_client):
        resp = pg_client.get("/api/loan-payments/not-a-uuid")
        assert resp.status_code == 422

    def test_data_persists_in_postgresql(self, pg_client, pg_session):
        """Verify round-trip: create → retrieve from real PostgreSQL."""
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid, confirmation_number="PG-ROUND-001")
        fetched = pg_client.get(f"/api/loan-payments/{created['id']}").json()
        assert fetched["confirmation_number"] == "PG-ROUND-001"


# ---------------------------------------------------------------------------
# LIST — GET /api/loan-payments
# ---------------------------------------------------------------------------

class TestListPaymentsIntegration:

    def test_list_returns_200(self, pg_client):
        resp = pg_client.get("/api/loan-payments")
        assert resp.status_code == 200

    def test_list_returns_array(self, pg_client):
        data = pg_client.get("/api/loan-payments").json()
        assert isinstance(data, list)

    def test_created_payments_appear_in_list(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        _create_payment(pg_client, lid)
        _create_payment(pg_client, lid)
        data = pg_client.get(f"/api/loan-payments?loan_application_id={lid}").json()
        assert len(data) == 2

    def test_filter_by_status_paid(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        _create_payment(pg_client, lid, status="PAID")
        _create_payment(pg_client, lid, status="PENDING")
        data = pg_client.get(
            f"/api/loan-payments?loan_application_id={lid}&status=PAID"
        ).json()
        assert len(data) == 1
        assert data[0]["status"] == "PAID"

    def test_filter_by_due_date_range(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        today = date.today()
        past = today - timedelta(days=30)
        future = today + timedelta(days=30)
        _create_payment(pg_client, lid, due_date=str(past))
        _create_payment(pg_client, lid, due_date=str(today))
        _create_payment(pg_client, lid, due_date=str(future))
        data = pg_client.get(
            f"/api/loan-payments?loan_application_id={lid}"
            f"&due_date_from={today}&due_date_to={today}"
        ).json()
        assert len(data) == 1
        assert data[0]["due_date"] == str(today)

    def test_list_ordered_by_due_date(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        today = date.today()
        _create_payment(pg_client, lid, due_date=str(today + timedelta(days=10)))
        _create_payment(pg_client, lid, due_date=str(today - timedelta(days=10)))
        _create_payment(pg_client, lid, due_date=str(today))
        data = pg_client.get(
            f"/api/loan-payments?loan_application_id={lid}"
        ).json()
        dates = [d["due_date"] for d in data]
        assert dates == sorted(dates)

    def test_invalid_loan_application_id_returns_422(self, pg_client):
        resp = pg_client.get("/api/loan-payments?loan_application_id=not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# UPDATE — PUT /api/loan-payments/{id}
# ---------------------------------------------------------------------------

class TestReplacePaymentIntegration:

    def test_put_returns_200(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid, status="PENDING")
        payload = _payment_payload(lid, status="PAID")
        resp = pg_client.put(f"/api/loan-payments/{created['id']}", json=payload)
        assert resp.status_code == 200

    def test_put_replaces_status(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid, status="PENDING")
        payload = _payment_payload(lid, status="PAID", payment_method="ACH")
        updated = pg_client.put(
            f"/api/loan-payments/{created['id']}", json=payload
        ).json()
        assert updated["status"] == "PAID"
        assert updated["payment_method"] == "ACH"

    def test_put_id_unchanged(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid)
        payload = _payment_payload(lid, status="PAID")
        updated = pg_client.put(
            f"/api/loan-payments/{created['id']}", json=payload
        ).json()
        assert updated["id"] == created["id"]

    def test_put_nonexistent_returns_404(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        resp = pg_client.put(
            f"/api/loan-payments/{uuid.uuid4()}", json=_payment_payload(lid)
        )
        assert resp.status_code == 404

    def test_put_invalid_uuid_returns_422(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        resp = pg_client.put(
            "/api/loan-payments/not-a-uuid", json=_payment_payload(lid)
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PARTIAL UPDATE — PATCH /api/loan-payments/{id}
# ---------------------------------------------------------------------------

class TestPatchPaymentIntegration:

    def test_patch_returns_200(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid, status="PENDING")
        resp = pg_client.patch(
            f"/api/loan-payments/{created['id']}", json={"status": "PAID"}
        )
        assert resp.status_code == 200

    def test_patch_updates_status(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid, status="PENDING")
        updated = pg_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "PAID", "paid_date": str(date.today())},
        ).json()
        assert updated["status"] == "PAID"

    def test_patch_preserves_untouched_fields(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(
            pg_client, lid, total_amount="2000.00", borrower_name="Keep Me"
        )
        updated = pg_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "PAID"},
        ).json()
        assert float(updated["total_amount"]) == 2000.0
        assert updated["borrower_name"] == "Keep Me"

    def test_patch_late_fee(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid, status="PENDING")
        updated = pg_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "LATE", "late_fee": "35.00"},
        ).json()
        assert updated["status"] == "LATE"
        assert float(updated["late_fee"]) == 35.0

    def test_patch_nonexistent_returns_404(self, pg_client):
        resp = pg_client.patch(
            f"/api/loan-payments/{uuid.uuid4()}", json={"status": "PAID"}
        )
        assert resp.status_code == 404

    def test_patch_invalid_status_returns_422(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid)
        resp = pg_client.patch(
            f"/api/loan-payments/{created['id']}", json={"status": "JUNK"}
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE — DELETE /api/loan-payments/{id}
# ---------------------------------------------------------------------------

class TestDeletePaymentIntegration:

    def test_delete_returns_204(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid)
        resp = pg_client.delete(f"/api/loan-payments/{created['id']}")
        assert resp.status_code == 204

    def test_delete_removes_record(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid)
        pid = created["id"]
        pg_client.delete(f"/api/loan-payments/{pid}")
        get_resp = pg_client.get(f"/api/loan-payments/{pid}")
        assert get_resp.status_code == 404

    def test_delete_nonexistent_returns_404(self, pg_client):
        resp = pg_client.delete(f"/api/loan-payments/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_delete_removes_only_target(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        p1 = _create_payment(pg_client, lid)
        p2 = _create_payment(pg_client, lid)
        pg_client.delete(f"/api/loan-payments/{p2['id']}")
        remaining = pg_client.get(
            f"/api/loan-payments?loan_application_id={lid}"
        ).json()
        assert len(remaining) == 1
        assert remaining[0]["id"] == p1["id"]

    def test_delete_invalid_uuid_returns_422(self, pg_client):
        resp = pg_client.delete("/api/loan-payments/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# OVERDUE — GET /api/loan-payments/overdue
# ---------------------------------------------------------------------------

class TestOverduePaymentsIntegration:

    def test_overdue_returns_200(self, pg_client):
        resp = pg_client.get("/api/loan-payments/overdue")
        assert resp.status_code == 200

    def test_overdue_returns_list(self, pg_client):
        data = pg_client.get("/api/loan-payments/overdue").json()
        assert isinstance(data, list)

    def test_past_pending_detected_as_overdue(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        past_date = date.today() - timedelta(days=15)
        created = _create_payment(pg_client, lid, status="PENDING", due_date=str(past_date))
        data = pg_client.get("/api/loan-payments/overdue").json()
        ids = [p["id"] for p in data]
        assert created["id"] in ids

    def test_paid_past_not_overdue(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        past_date = date.today() - timedelta(days=15)
        created = _create_payment(pg_client, lid, status="PAID", due_date=str(past_date))
        data = pg_client.get("/api/loan-payments/overdue").json()
        ids = [p["id"] for p in data]
        assert created["id"] not in ids

    def test_future_pending_not_overdue(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        future = date.today() + timedelta(days=15)
        created = _create_payment(pg_client, lid, status="PENDING", due_date=str(future))
        data = pg_client.get("/api/loan-payments/overdue").json()
        ids = [p["id"] for p in data]
        assert created["id"] not in ids

    def test_overdue_with_custom_as_of_date(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        five_days_ago = date.today() - timedelta(days=5)
        created = _create_payment(
            pg_client, lid, status="PENDING", due_date=str(five_days_ago)
        )
        future_as_of = date.today() + timedelta(days=1)
        data = pg_client.get(f"/api/loan-payments/overdue?as_of={future_as_of}").json()
        ids = [p["id"] for p in data]
        assert created["id"] in ids


# ---------------------------------------------------------------------------
# SUMMARY — GET /api/loan-payments/summary/{loan_application_id}
# ---------------------------------------------------------------------------

class TestPaymentSummaryIntegration:

    def test_summary_returns_200(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        resp = pg_client.get(f"/api/loan-payments/summary/{lid}")
        assert resp.status_code == 200

    def test_summary_empty_for_new_loan(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        data = pg_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert data["total_payments"] == 0
        assert float(data["total_paid"]) == 0.0
        assert float(data["total_outstanding"]) == 0.0

    def test_summary_aggregates_correctly(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        _create_payment(pg_client, lid, status="PAID", total_amount="1000.00")
        _create_payment(pg_client, lid, status="PENDING", total_amount="800.00")
        _create_payment(
            pg_client, lid, status="LATE", total_amount="800.00", late_fee="25.00"
        )

        data = pg_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert data["total_payments"] == 3
        assert data["paid_count"] == 1
        assert data["late_count"] == 1
        assert data["pending_count"] == 1
        assert float(data["total_paid"]) == pytest.approx(1000.0)
        assert float(data["total_outstanding"]) == pytest.approx(1600.0)
        assert float(data["total_late_fees"]) == pytest.approx(25.0)

    def test_summary_contains_loan_application_id(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        data = pg_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert data["loan_application_id"] == str(lid)

    def test_summary_all_status_counts(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        for status in ("PAID", "PENDING", "LATE", "MISSED", "PARTIAL"):
            _create_payment(pg_client, lid, status=status, total_amount="100.00")
        data = pg_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert data["total_payments"] == 5
        assert data["paid_count"] == 1
        assert data["pending_count"] == 1
        assert data["late_count"] == 1
        assert data["missed_count"] == 1
        assert data["partial_count"] == 1

    def test_summary_invalid_uuid_returns_422(self, pg_client):
        resp = pg_client.get("/api/loan-payments/summary/not-a-uuid")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# End-to-end lifecycle test
# ---------------------------------------------------------------------------

class TestFullLifecycleIntegration:

    def test_create_retrieve_update_delete_lifecycle(self, pg_client, pg_session):
        # Create
        lid = _make_loan_app(pg_session)
        created = _create_payment(
            pg_client, lid,
            status="PENDING",
            borrower_name="Lifecycle Test",
            total_amount="1500.00",
        )
        pid = created["id"]

        # Read
        fetched = pg_client.get(f"/api/loan-payments/{pid}").json()
        assert fetched["borrower_name"] == "Lifecycle Test"

        # Patch
        patched = pg_client.patch(
            f"/api/loan-payments/{pid}",
            json={"status": "PAID", "paid_date": str(date.today())},
        ).json()
        assert patched["status"] == "PAID"

        # Confirm appears in list
        listing = pg_client.get(
            f"/api/loan-payments?loan_application_id={lid}"
        ).json()
        assert any(p["id"] == pid for p in listing)

        # Delete
        del_resp = pg_client.delete(f"/api/loan-payments/{pid}")
        assert del_resp.status_code == 204

        # Confirm gone
        gone = pg_client.get(f"/api/loan-payments/{pid}")
        assert gone.status_code == 404

    def test_summary_updates_after_status_change(self, pg_client, pg_session):
        lid = _make_loan_app(pg_session)
        created = _create_payment(pg_client, lid, status="PENDING", total_amount="1000.00")

        before = pg_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert before["pending_count"] == 1
        assert before["paid_count"] == 0

        pg_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "PAID", "paid_date": str(date.today())},
        )

        after = pg_client.get(f"/api/loan-payments/summary/{lid}").json()
        assert after["pending_count"] == 0
        assert after["paid_count"] == 1
        assert float(after["total_paid"]) == pytest.approx(1000.0)
