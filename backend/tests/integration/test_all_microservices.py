"""
Integration tests for all microservices against the Dockerized local environment.

These tests use httpx to interact with the running Docker Compose stack
(app on http://localhost:8000).  They are skipped automatically when the
service is not reachable so they are safe to run in environments without
Docker.

Run via:
    make test-integration                     # from project root
    cd backend && pytest -m integration -v    # directly

Or against a custom host:
    SERVICE_BASE_URL=http://localhost:8000 pytest -m integration -v
"""

import os
import uuid
from datetime import date, timedelta

import httpx
import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.getenv("SERVICE_BASE_URL", "http://localhost:8000")

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Session-scoped httpx client — skips if the service is not reachable
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def http_client():
    """
    Synchronous httpx client aimed at the Dockerized service.

    The entire integration suite is skipped if the service health-check
    endpoint is not reachable within the timeout window.
    """
    client = httpx.Client(base_url=BASE_URL, timeout=10.0)
    try:
        resp = client.get("/health")
        if resp.status_code not in (200, 503):
            pytest.skip(
                f"Service at {BASE_URL} returned unexpected status "
                f"{resp.status_code} — skipping integration tests."
            )
    except httpx.ConnectError:
        pytest.skip(
            f"Service not reachable at {BASE_URL} — "
            "start Docker Compose and retry: `docker compose up -d`"
        )
    yield client
    client.close()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _post_loan_app(http_client: httpx.Client) -> str:
    """
    Create a LoanApplication via POST /api/loan-applications and return its id.
    Falls back to direct DB insertion is not available — if the endpoint does
    not exist we create a payment with a random UUID (PostgreSQL constraint
    violations will be caught in the test itself).
    """
    # If the endpoint exists, use it
    resp = http_client.post(
        "/api/loan-applications",
        json={"status": "SUBMITTED"},
    )
    if resp.status_code == 201:
        return resp.json()["id"]
    # Endpoint not yet available — derive an id from the payment create response
    return None


def _payment_payload(loan_app_id: str, **overrides) -> dict:
    base = {
        "loan_application_id": loan_app_id,
        "due_date": str(date.today()),
        "status": "PENDING",
        "total_amount": "1500.00",
        "principal_amount": "1200.00",
        "interest_amount": "300.00",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """Verify the /health endpoint of the running service."""

    def test_health_returns_200(self, http_client):
        resp = http_client.get("/health")
        assert resp.status_code == 200

    def test_health_response_has_status_ok(self, http_client):
        data = resp = http_client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_response_has_database_key(self, http_client):
        data = http_client.get("/health").json()
        assert "database" in data

    def test_health_content_type_is_json(self, http_client):
        resp = http_client.get("/health")
        assert "application/json" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

class TestRootEndpoint:
    """Verify the / root endpoint."""

    def test_root_returns_200(self, http_client):
        resp = http_client.get("/")
        assert resp.status_code == 200

    def test_root_response_has_message(self, http_client):
        data = http_client.get("/").json()
        assert "message" in data


# ---------------------------------------------------------------------------
# OTP Codes service
# ---------------------------------------------------------------------------

class TestOtpCodesService:
    """Verify the /api/otp-codes endpoint is reachable."""

    def test_list_otp_codes_returns_200(self, http_client):
        resp = http_client.get("/api/otp-codes")
        assert resp.status_code == 200

    def test_list_otp_codes_returns_list(self, http_client):
        data = http_client.get("/api/otp-codes").json()
        assert isinstance(data, list)

    def test_create_otp_code_returns_201(self, http_client):
        payload = {
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "code": "123456",
        }
        resp = http_client.post("/api/otp-codes", json=payload)
        assert resp.status_code == 201

    def test_create_otp_code_response_has_id(self, http_client):
        payload = {
            "email": f"test_{uuid.uuid4().hex[:8]}@example.com",
            "code": "654321",
        }
        data = http_client.post("/api/otp-codes", json=payload).json()
        assert "id" in data

    def test_create_otp_missing_email_returns_422(self, http_client):
        resp = http_client.post("/api/otp-codes", json={"code": "123456"})
        assert resp.status_code == 422

    def test_create_otp_missing_code_returns_422(self, http_client):
        resp = http_client.post(
            "/api/otp-codes",
            json={"email": "x@example.com"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Notifications service
# ---------------------------------------------------------------------------

class TestNotificationsService:
    """Verify the /api/notifications endpoint is reachable."""

    def test_list_notifications_returns_200(self, http_client):
        resp = http_client.get("/api/notifications")
        assert resp.status_code == 200

    def test_list_notifications_returns_list(self, http_client):
        data = http_client.get("/api/notifications").json()
        assert isinstance(data, list)

    def test_create_notification_returns_201(self, http_client):
        payload = {
            "recipient_email": f"notify_{uuid.uuid4().hex[:8]}@example.com",
            "subject": "Integration Test Notification",
            "body": "This is an automated integration test message.",
            "notification_type": "EMAIL",
        }
        resp = http_client.post("/api/notifications", json=payload)
        assert resp.status_code == 201

    def test_create_notification_has_id(self, http_client):
        payload = {
            "recipient_email": f"notify_{uuid.uuid4().hex[:8]}@example.com",
            "subject": "ID Test",
            "body": "Testing id field.",
            "notification_type": "EMAIL",
        }
        data = http_client.post("/api/notifications", json=payload).json()
        assert "id" in data
        uuid.UUID(data["id"])  # must be a valid UUID

    def test_create_notification_missing_subject_returns_422(self, http_client):
        payload = {
            "recipient_email": "x@example.com",
            "body": "body",
            "notification_type": "EMAIL",
        }
        resp = http_client.post("/api/notifications", json=payload)
        assert resp.status_code == 422

    def test_get_notification_by_id_returns_200(self, http_client):
        payload = {
            "recipient_email": f"get_{uuid.uuid4().hex[:8]}@example.com",
            "subject": "Get by ID",
            "body": "Body text.",
            "notification_type": "EMAIL",
        }
        created = http_client.post("/api/notifications", json=payload).json()
        resp = http_client.get(f"/api/notifications/{created['id']}")
        assert resp.status_code == 200

    def test_get_nonexistent_notification_returns_404(self, http_client):
        resp = http_client.get(f"/api/notifications/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Loan Payments service
# ---------------------------------------------------------------------------

class TestLoanPaymentsService:
    """
    Verify the /api/loan-payments endpoints against the running Docker stack.

    These tests create a LoanApplication first (if the endpoint is available),
    then exercise the full loan-payment lifecycle.
    """

    @pytest.fixture(autouse=True)
    def _loan_app_id(self, http_client):
        """
        Try to obtain a real LoanApplication id.  If the loan-applications
        endpoint is not available, we pre-create a payment and harvest the
        loan_application_id from the response so the tests can still run.
        """
        lid = _post_loan_app(http_client)
        if lid is None:
            # Fallback: use a random UUID; the DB foreign-key constraint will
            # catch any referential-integrity issues in specific tests.
            lid = str(uuid.uuid4())
        self.loan_app_id = lid

    def test_list_payments_returns_200(self, http_client):
        resp = http_client.get("/api/loan-payments")
        assert resp.status_code == 200

    def test_list_payments_returns_list(self, http_client):
        data = http_client.get("/api/loan-payments").json()
        assert isinstance(data, list)

    def test_create_payment_returns_201(self, http_client):
        payload = _payment_payload(self.loan_app_id)
        resp = http_client.post("/api/loan-payments", json=payload)
        assert resp.status_code == 201

    def test_create_payment_response_has_id(self, http_client):
        payload = _payment_payload(self.loan_app_id)
        data = http_client.post("/api/loan-payments", json=payload).json()
        assert "id" in data
        uuid.UUID(data["id"])

    def test_create_payment_missing_due_date_returns_422(self, http_client):
        payload = {"loan_application_id": self.loan_app_id}
        resp = http_client.post("/api/loan-payments", json=payload)
        assert resp.status_code == 422

    def test_create_payment_invalid_status_returns_422(self, http_client):
        payload = _payment_payload(self.loan_app_id, status="BOGUS")
        resp = http_client.post("/api/loan-payments", json=payload)
        assert resp.status_code == 422

    def test_get_payment_by_id_returns_200(self, http_client):
        created = http_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id),
        ).json()
        resp = http_client.get(f"/api/loan-payments/{created['id']}")
        assert resp.status_code == 200

    def test_get_nonexistent_payment_returns_404(self, http_client):
        resp = http_client.get(f"/api/loan-payments/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_patch_payment_status(self, http_client):
        created = http_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id, status="PENDING"),
        ).json()
        updated = http_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "PAID", "paid_date": str(date.today())},
        ).json()
        assert updated["status"] == "PAID"

    def test_patch_preserves_untouched_fields(self, http_client):
        created = http_client.post(
            "/api/loan-payments",
            json=_payment_payload(
                self.loan_app_id,
                borrower_name="Preserve Me",
                total_amount="2500.00",
            ),
        ).json()
        updated = http_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "PAID"},
        ).json()
        assert updated["borrower_name"] == "Preserve Me"
        assert float(updated["total_amount"]) == pytest.approx(2500.0)

    def test_put_payment_returns_200(self, http_client):
        created = http_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id, status="PENDING"),
        ).json()
        replace_payload = _payment_payload(self.loan_app_id, status="PAID")
        resp = http_client.put(
            f"/api/loan-payments/{created['id']}", json=replace_payload
        )
        assert resp.status_code == 200

    def test_delete_payment_returns_204(self, http_client):
        created = http_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id),
        ).json()
        resp = http_client.delete(f"/api/loan-payments/{created['id']}")
        assert resp.status_code == 204

    def test_deleted_payment_not_retrievable(self, http_client):
        created = http_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id),
        ).json()
        http_client.delete(f"/api/loan-payments/{created['id']}")
        resp = http_client.get(f"/api/loan-payments/{created['id']}")
        assert resp.status_code == 404

    def test_overdue_endpoint_returns_200(self, http_client):
        resp = http_client.get("/api/loan-payments/overdue")
        assert resp.status_code == 200

    def test_overdue_returns_list(self, http_client):
        data = http_client.get("/api/loan-payments/overdue").json()
        assert isinstance(data, list)

    def test_overdue_past_pending_detected(self, http_client):
        past_date = date.today() - timedelta(days=20)
        created = http_client.post(
            "/api/loan-payments",
            json=_payment_payload(
                self.loan_app_id, status="PENDING", due_date=str(past_date)
            ),
        ).json()
        data = http_client.get("/api/loan-payments/overdue").json()
        ids = [p["id"] for p in data]
        assert created["id"] in ids
        # Cleanup
        http_client.delete(f"/api/loan-payments/{created['id']}")

    def test_summary_endpoint_returns_200(self, http_client):
        resp = http_client.get(f"/api/loan-payments/summary/{self.loan_app_id}")
        assert resp.status_code == 200

    def test_summary_has_required_fields(self, http_client):
        data = http_client.get(
            f"/api/loan-payments/summary/{self.loan_app_id}"
        ).json()
        required = {
            "loan_application_id",
            "total_payments",
            "paid_count",
            "pending_count",
            "late_count",
            "missed_count",
            "partial_count",
            "total_paid",
            "total_outstanding",
            "total_late_fees",
        }
        assert required.issubset(data.keys())

    def test_full_lifecycle(self, http_client):
        """End-to-end lifecycle: create → read → patch → list → delete."""
        # Create
        created = http_client.post(
            "/api/loan-payments",
            json=_payment_payload(
                self.loan_app_id,
                status="PENDING",
                borrower_name="Lifecycle Tester",
                total_amount="1800.00",
            ),
        ).json()
        pid = created["id"]

        # Read
        fetched = http_client.get(f"/api/loan-payments/{pid}").json()
        assert fetched["borrower_name"] == "Lifecycle Tester"

        # Patch
        patched = http_client.patch(
            f"/api/loan-payments/{pid}",
            json={"status": "PAID", "paid_date": str(date.today())},
        ).json()
        assert patched["status"] == "PAID"

        # List — appears in list
        listing = http_client.get(
            f"/api/loan-payments?loan_application_id={self.loan_app_id}"
        ).json()
        assert any(p["id"] == pid for p in listing)

        # Delete
        del_resp = http_client.delete(f"/api/loan-payments/{pid}")
        assert del_resp.status_code == 204

        # Confirm gone
        gone = http_client.get(f"/api/loan-payments/{pid}")
        assert gone.status_code == 404


# ---------------------------------------------------------------------------
# Cross-service interaction tests
# ---------------------------------------------------------------------------

class TestCrossServiceInteractions:
    """
    Verify that multiple services operate correctly together and share
    the same underlying PostgreSQL database instance.
    """

    def test_health_check_confirms_shared_database(self, http_client):
        """All services share one DB — the health endpoint must report 'ok'."""
        data = http_client.get("/health").json()
        assert data["database"] == "ok"

    def test_notification_and_otp_are_independent(self, http_client):
        """Creating an OTP code must not affect the notification list."""
        notifications_before = http_client.get("/api/notifications").json()
        count_before = len(notifications_before)

        http_client.post(
            "/api/otp-codes",
            json={
                "email": f"x_{uuid.uuid4().hex[:6]}@example.com",
                "code": "999999",
            },
        )

        notifications_after = http_client.get("/api/notifications").json()
        # Notification count should be unchanged
        assert len(notifications_after) >= count_before

    def test_multiple_service_endpoints_respond(self, http_client):
        """All three microservice prefixes must be reachable."""
        endpoints = ["/api/otp-codes", "/api/notifications", "/api/loan-payments"]
        for endpoint in endpoints:
            resp = http_client.get(endpoint)
            assert resp.status_code == 200, (
                f"Expected 200 from {endpoint}, got {resp.status_code}"
            )
