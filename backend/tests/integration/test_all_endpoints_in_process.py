"""
In-process integration tests for ALL microservice endpoints.

These tests exercise the full request→router→DB chain using FastAPI's
TestClient backed by an in-memory SQLite database.  No running Docker
container or PostgreSQL instance is required, making them fully CI/CD
safe.

Coverage matrix
───────────────
  /                                   — root
  /health                             — health check
  /api/otp-codes                      — OTP CRUD + auth
  /api/auth/send-otp                  — OTP send
  /api/auth/verify-otp                — OTP verify
  /api/notifications                  — Notification CRUD + read
  /api/loan-payments                  — LoanPayment CRUD + overdue + summary
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.models.loan_application import LoanApplication
from app.models.otp_code import OtpCode


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_loan_app(db_session) -> str:
    """Insert a minimal LoanApplication and return its UUID string."""
    obj = LoanApplication(status="SUBMITTED")
    db_session.add(obj)
    db_session.commit()
    db_session.refresh(obj)
    return str(obj.id)


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


def _insert_otp(
    db_session,
    email: str = "test@example.com",
    code: str = "123456",
    used: bool = False,
    offset_minutes: int = 10,
) -> OtpCode:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    otp = OtpCode(email=email, code=code, expires_at=expires_at, used=used)
    db_session.add(otp)
    db_session.commit()
    db_session.refresh(otp)
    return otp


# ─────────────────────────────────────────────────────────────────────────────
# Root endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestRootEndpoint:
    def test_root_returns_200(self, app_client: TestClient):
        resp = app_client.get("/")
        assert resp.status_code == 200

    def test_root_has_message(self, app_client: TestClient):
        data = app_client.get("/").json()
        assert "message" in data
        assert isinstance(data["message"], str)
        assert len(data["message"]) > 0

    def test_root_response_is_json(self, app_client: TestClient):
        resp = app_client.get("/")
        assert "application/json" in resp.headers.get("content-type", "")


# ─────────────────────────────────────────────────────────────────────────────
# Health endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self, app_client: TestClient):
        resp = app_client.get("/health")
        assert resp.status_code == 200

    def test_health_has_status_field(self, app_client: TestClient):
        data = app_client.get("/health").json()
        assert "status" in data

    def test_health_has_database_field(self, app_client: TestClient):
        data = app_client.get("/health").json()
        assert "database" in data

    def test_health_has_last_checked_field(self, app_client: TestClient):
        data = app_client.get("/health").json()
        assert "last_checked" in data

    def test_health_content_type_is_json(self, app_client: TestClient):
        resp = app_client.get("/health")
        assert "application/json" in resp.headers.get("content-type", "")

    def test_health_method_not_allowed(self, app_client: TestClient):
        resp = app_client.post("/health")
        assert resp.status_code == 405


# ─────────────────────────────────────────────────────────────────────────────
# OTP Codes endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestOtpCodesEndpoints:
    """Tests for all /api/otp-codes and /api/auth/* endpoints."""

    # --- send-otp ---

    def test_send_otp_returns_200(self, app_client: TestClient):
        resp = app_client.post(
            "/api/auth/send-otp", json={"email": "user@example.com"}
        )
        assert resp.status_code == 200

    def test_send_otp_has_message(self, app_client: TestClient):
        data = app_client.post(
            "/api/auth/send-otp", json={"email": "user@example.com"}
        ).json()
        assert "message" in data

    def test_send_otp_creates_record(self, app_client: TestClient, db_session):
        email = f"create_{uuid.uuid4().hex[:6]}@example.com"
        app_client.post("/api/auth/send-otp", json={"email": email})
        otp = (
            db_session.query(OtpCode)
            .filter(OtpCode.email == email)
            .first()
        )
        assert otp is not None

    def test_send_otp_invalid_email_returns_422(self, app_client: TestClient):
        resp = app_client.post("/api/auth/send-otp", json={"email": "not-an-email"})
        assert resp.status_code == 422

    def test_send_otp_missing_email_returns_422(self, app_client: TestClient):
        resp = app_client.post("/api/auth/send-otp", json={})
        assert resp.status_code == 422

    def test_send_otp_get_method_returns_405(self, app_client: TestClient):
        resp = app_client.get("/api/auth/send-otp")
        assert resp.status_code == 405

    # --- verify-otp ---

    def test_verify_otp_valid_code_returns_200(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="verify@example.com", code="111111")
        resp = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "verify@example.com", "code": "111111"},
        )
        assert resp.status_code == 200

    def test_verify_otp_returns_token(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="token@example.com", code="222222")
        data = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "token@example.com", "code": "222222"},
        ).json()
        assert "token" in data
        assert isinstance(data["token"], str)
        assert len(data["token"]) > 0

    def test_verify_otp_returns_email(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="emailfield@example.com", code="333333")
        data = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "emailfield@example.com", "code": "333333"},
        ).json()
        assert data["email"] == "emailfield@example.com"

    def test_verify_otp_wrong_code_returns_401(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="wrong@example.com", code="444444")
        resp = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "wrong@example.com", "code": "000000"},
        )
        assert resp.status_code == 401

    def test_verify_otp_no_record_returns_401(self, app_client: TestClient):
        resp = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "ghost@example.com", "code": "555555"},
        )
        assert resp.status_code == 401

    def test_verify_otp_expired_returns_401(self, app_client: TestClient, db_session):
        _insert_otp(
            db_session, email="expired@example.com", code="666666", offset_minutes=-5
        )
        resp = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "expired@example.com", "code": "666666"},
        )
        assert resp.status_code == 401

    def test_verify_otp_used_returns_401(self, app_client: TestClient, db_session):
        _insert_otp(
            db_session, email="used@example.com", code="777777", used=True
        )
        resp = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "used@example.com", "code": "777777"},
        )
        assert resp.status_code == 401

    def test_verify_otp_marks_otp_used(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="markused@example.com", code="888888")
        app_client.post(
            "/api/auth/verify-otp",
            json={"email": "markused@example.com", "code": "888888"},
        )
        db_session.refresh(otp)
        assert otp.used is True

    def test_verify_otp_missing_code_returns_422(self, app_client: TestClient):
        resp = app_client.post(
            "/api/auth/verify-otp", json={"email": "x@example.com"}
        )
        assert resp.status_code == 422

    def test_verify_otp_get_method_returns_405(self, app_client: TestClient):
        resp = app_client.get("/api/auth/verify-otp")
        assert resp.status_code == 405

    # --- list otp-codes ---

    def test_list_otp_codes_returns_200(self, app_client: TestClient):
        resp = app_client.get("/api/otp-codes")
        assert resp.status_code == 200

    def test_list_otp_codes_returns_list(self, app_client: TestClient):
        data = app_client.get("/api/otp-codes").json()
        assert isinstance(data, list)

    def test_list_otp_codes_populated(self, app_client: TestClient, db_session):
        email = f"list_{uuid.uuid4().hex[:6]}@example.com"
        _insert_otp(db_session, email=email)
        data = app_client.get(f"/api/otp-codes?email={email}").json()
        assert len(data) >= 1
        assert all(r["email"] == email for r in data)

    def test_list_otp_codes_no_code_field(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="nocodeexpect@example.com")
        data = app_client.get("/api/otp-codes").json()
        for record in data:
            assert "code" not in record

    def test_list_otp_codes_filter_by_used(self, app_client: TestClient, db_session):
        email = f"filt_{uuid.uuid4().hex[:6]}@example.com"
        _insert_otp(db_session, email=email, used=True, code="100100")
        _insert_otp(db_session, email=email, used=False, code="200200")
        used_data = app_client.get(f"/api/otp-codes?email={email}&used=true").json()
        assert all(r["used"] is True for r in used_data)
        unused_data = app_client.get(f"/api/otp-codes?email={email}&used=false").json()
        assert all(r["used"] is False for r in unused_data)

    # --- get single otp-code ---

    def test_get_otp_code_returns_200(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="single@example.com")
        resp = app_client.get(f"/api/otp-codes/{otp.id}")
        assert resp.status_code == 200

    def test_get_otp_code_has_id(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="single2@example.com")
        data = app_client.get(f"/api/otp-codes/{otp.id}").json()
        assert data["id"] == str(otp.id)

    def test_get_otp_code_no_code_field(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="noleak@example.com")
        data = app_client.get(f"/api/otp-codes/{otp.id}").json()
        assert "code" not in data

    def test_get_otp_code_not_found_returns_404(self, app_client: TestClient):
        resp = app_client.get(f"/api/otp-codes/{uuid.uuid4()}")
        assert resp.status_code == 404

    # --- delete otp-code ---

    def test_delete_otp_code_returns_204(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="del@example.com")
        resp = app_client.delete(f"/api/otp-codes/{otp.id}")
        assert resp.status_code == 204

    def test_delete_otp_code_removed(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="del2@example.com")
        app_client.delete(f"/api/otp-codes/{otp.id}")
        resp = app_client.get(f"/api/otp-codes/{otp.id}")
        assert resp.status_code == 404

    def test_delete_otp_code_not_found_returns_404(self, app_client: TestClient):
        resp = app_client.delete(f"/api/otp-codes/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_delete_otp_list_endpoint_returns_405(self, app_client: TestClient):
        resp = app_client.delete("/api/otp-codes")
        assert resp.status_code == 405

    # --- rate limiting ---

    def test_otp_rate_limit_429_after_five(self, app_client: TestClient, db_session):
        email = f"rl_{uuid.uuid4().hex[:6]}@example.com"
        for _ in range(5):
            _insert_otp(db_session, email=email, code="999999")
        resp = app_client.post("/api/auth/send-otp", json={"email": email})
        assert resp.status_code == 429


# ─────────────────────────────────────────────────────────────────────────────
# Notification endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestNotificationEndpoints:
    """Tests for all /api/notifications/* endpoints."""

    def _create(self, client: TestClient, **overrides) -> dict:
        payload = {
            "title": "Integration Test",
            "message": "This is a test notification message.",
            "type": "INFO",
        }
        payload.update(overrides)
        resp = client.post("/api/notifications", json=payload)
        assert resp.status_code == 201, resp.text
        return resp.json()

    # --- create ---

    def test_create_notification_returns_201(self, app_client: TestClient):
        resp = app_client.post(
            "/api/notifications",
            json={"title": "T", "message": "M"},
        )
        assert resp.status_code == 201

    def test_create_notification_has_id(self, app_client: TestClient):
        data = self._create(app_client)
        assert "id" in data
        uuid.UUID(data["id"])  # valid UUID

    def test_create_notification_has_created_at(self, app_client: TestClient):
        data = self._create(app_client)
        assert "created_at" in data

    def test_create_notification_is_read_false(self, app_client: TestClient):
        data = self._create(app_client)
        assert data["is_read"] is False

    def test_create_notification_missing_title_returns_422(self, app_client: TestClient):
        resp = app_client.post("/api/notifications", json={"message": "M"})
        assert resp.status_code == 422

    def test_create_notification_missing_message_returns_422(self, app_client: TestClient):
        resp = app_client.post("/api/notifications", json={"title": "T"})
        assert resp.status_code == 422

    def test_create_notification_title_too_long_returns_422(self, app_client: TestClient):
        resp = app_client.post(
            "/api/notifications",
            json={"title": "x" * 256, "message": "M"},
        )
        assert resp.status_code == 422

    def test_create_notification_with_user_email(self, app_client: TestClient):
        data = self._create(app_client, user_email="notify@example.com")
        assert data["user_email"] == "notify@example.com"

    def test_create_notification_with_optional_fields(self, app_client: TestClient):
        uid = str(uuid.uuid4())
        data = self._create(
            app_client,
            user_id=uid,
            user_name="Alice",
            link="https://example.com",
            type="ALERT",
        )
        assert data["user_id"] == uid
        assert data["user_name"] == "Alice"
        assert data["link"] == "https://example.com"
        assert data["type"] == "ALERT"

    # --- list ---

    def test_list_notifications_returns_200(self, app_client: TestClient):
        resp = app_client.get("/api/notifications")
        assert resp.status_code == 200

    def test_list_notifications_returns_list(self, app_client: TestClient):
        data = app_client.get("/api/notifications").json()
        assert isinstance(data, list)

    def test_list_notifications_contains_created(self, app_client: TestClient):
        created = self._create(app_client, title="Findable")
        data = app_client.get("/api/notifications").json()
        ids = [n["id"] for n in data]
        assert created["id"] in ids

    def test_list_notifications_filter_by_user_id(self, app_client: TestClient):
        uid = str(uuid.uuid4())
        created = self._create(app_client, user_id=uid)
        data = app_client.get(f"/api/notifications?user_id={uid}").json()
        assert len(data) >= 1
        assert all(n["user_id"] == uid for n in data)

    def test_list_notifications_unread_only_filter(self, app_client: TestClient):
        uid = str(uuid.uuid4())
        n = self._create(app_client, user_id=uid)
        data = app_client.get(
            f"/api/notifications?user_id={uid}&unread_only=true"
        ).json()
        assert len(data) >= 1
        assert all(n["is_read"] is False for n in data)

    # --- get single ---

    def test_get_notification_returns_200(self, app_client: TestClient):
        created = self._create(app_client)
        resp = app_client.get(f"/api/notifications/{created['id']}")
        assert resp.status_code == 200

    def test_get_notification_has_correct_id(self, app_client: TestClient):
        created = self._create(app_client)
        data = app_client.get(f"/api/notifications/{created['id']}").json()
        assert data["id"] == created["id"]

    def test_get_notification_has_correct_title(self, app_client: TestClient):
        created = self._create(app_client, title="Unique Title XYZ")
        data = app_client.get(f"/api/notifications/{created['id']}").json()
        assert data["title"] == "Unique Title XYZ"

    def test_get_notification_not_found_returns_404(self, app_client: TestClient):
        resp = app_client.get(f"/api/notifications/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_get_notification_invalid_uuid_returns_422(self, app_client: TestClient):
        resp = app_client.get("/api/notifications/not-a-uuid")
        assert resp.status_code == 422

    # --- mark as read ---

    def test_mark_read_returns_200(self, app_client: TestClient):
        created = self._create(app_client)
        resp = app_client.patch(
            f"/api/notifications/{created['id']}/read",
            json={"is_read": True},
        )
        assert resp.status_code == 200

    def test_mark_read_sets_is_read_true(self, app_client: TestClient):
        created = self._create(app_client)
        data = app_client.patch(
            f"/api/notifications/{created['id']}/read",
            json={"is_read": True},
        ).json()
        assert data["is_read"] is True

    def test_mark_read_sets_read_at(self, app_client: TestClient):
        created = self._create(app_client)
        data = app_client.patch(
            f"/api/notifications/{created['id']}/read",
            json={"is_read": True},
        ).json()
        assert data["read_at"] is not None

    def test_mark_unread_clears_read_at(self, app_client: TestClient):
        created = self._create(app_client)
        app_client.patch(
            f"/api/notifications/{created['id']}/read",
            json={"is_read": True},
        )
        data = app_client.patch(
            f"/api/notifications/{created['id']}/read",
            json={"is_read": False},
        ).json()
        assert data["is_read"] is False
        assert data["read_at"] is None

    def test_mark_read_not_found_returns_404(self, app_client: TestClient):
        resp = app_client.patch(
            f"/api/notifications/{uuid.uuid4()}/read",
            json={"is_read": True},
        )
        assert resp.status_code == 404

    def test_put_on_notification_returns_405(self, app_client: TestClient):
        resp = app_client.put(
            f"/api/notifications/{uuid.uuid4()}",
            json={"title": "T", "message": "M"},
        )
        assert resp.status_code == 405

    # --- delete ---

    def test_delete_notification_returns_204(self, app_client: TestClient):
        created = self._create(app_client)
        resp = app_client.delete(f"/api/notifications/{created['id']}")
        assert resp.status_code == 204

    def test_delete_notification_removed(self, app_client: TestClient):
        created = self._create(app_client)
        app_client.delete(f"/api/notifications/{created['id']}")
        resp = app_client.get(f"/api/notifications/{created['id']}")
        assert resp.status_code == 404

    def test_delete_notification_not_found_returns_404(self, app_client: TestClient):
        resp = app_client.delete(f"/api/notifications/{uuid.uuid4()}")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Loan Payment endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestLoanPaymentEndpoints:
    """Tests for all /api/loan-payments/* endpoints."""

    @pytest.fixture(autouse=True)
    def _setup(self, db_session):
        self.loan_app_id = _make_loan_app(db_session)

    # --- create ---

    def test_create_payment_returns_201(self, app_client: TestClient):
        resp = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id),
        )
        assert resp.status_code == 201

    def test_create_payment_has_id(self, app_client: TestClient):
        data = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id),
        ).json()
        assert "id" in data
        uuid.UUID(data["id"])

    def test_create_payment_has_status(self, app_client: TestClient):
        data = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id, status="PENDING"),
        ).json()
        assert data["status"] == "PENDING"

    def test_create_payment_missing_due_date_returns_422(self, app_client: TestClient):
        resp = app_client.post(
            "/api/loan-payments",
            json={"loan_application_id": self.loan_app_id, "status": "PENDING"},
        )
        assert resp.status_code == 422

    def test_create_payment_invalid_status_returns_422(self, app_client: TestClient):
        resp = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id, status="INVALID"),
        )
        assert resp.status_code == 422

    def test_create_payment_stores_amounts(self, app_client: TestClient):
        data = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(
                self.loan_app_id,
                total_amount="2500.00",
                principal_amount="2000.00",
                interest_amount="500.00",
            ),
        ).json()
        assert float(data["total_amount"]) == pytest.approx(2500.0)

    # --- list ---

    def test_list_payments_returns_200(self, app_client: TestClient):
        resp = app_client.get("/api/loan-payments")
        assert resp.status_code == 200

    def test_list_payments_returns_list(self, app_client: TestClient):
        data = app_client.get("/api/loan-payments").json()
        assert isinstance(data, list)

    def test_list_payments_contains_created(self, app_client: TestClient):
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id),
        ).json()
        data = app_client.get("/api/loan-payments").json()
        ids = [p["id"] for p in data]
        assert created["id"] in ids

    def test_list_payments_filter_by_loan_app(self, app_client: TestClient):
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id),
        ).json()
        data = app_client.get(
            f"/api/loan-payments?loan_application_id={self.loan_app_id}"
        ).json()
        assert len(data) >= 1
        assert all(p["loan_application_id"] == self.loan_app_id for p in data)

    def test_list_payments_filter_by_status(self, app_client: TestClient):
        app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id, status="PENDING"),
        )
        data = app_client.get("/api/loan-payments?status=PENDING").json()
        assert len(data) >= 1
        assert all(p["status"] == "PENDING" for p in data)

    # --- get single ---

    def test_get_payment_returns_200(self, app_client: TestClient):
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id),
        ).json()
        resp = app_client.get(f"/api/loan-payments/{created['id']}")
        assert resp.status_code == 200

    def test_get_payment_has_correct_id(self, app_client: TestClient):
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id),
        ).json()
        data = app_client.get(f"/api/loan-payments/{created['id']}").json()
        assert data["id"] == created["id"]

    def test_get_payment_not_found_returns_404(self, app_client: TestClient):
        resp = app_client.get(f"/api/loan-payments/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_get_payment_invalid_uuid_returns_422(self, app_client: TestClient):
        resp = app_client.get("/api/loan-payments/not-a-uuid")
        assert resp.status_code == 422

    # --- patch ---

    def test_patch_payment_status(self, app_client: TestClient):
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id, status="PENDING"),
        ).json()
        updated = app_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "PAID", "paid_date": str(date.today())},
        ).json()
        assert updated["status"] == "PAID"

    def test_patch_preserves_untouched_fields(self, app_client: TestClient):
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(
                self.loan_app_id,
                borrower_name="Keep This",
                total_amount="3000.00",
            ),
        ).json()
        updated = app_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "PAID"},
        ).json()
        assert updated["borrower_name"] == "Keep This"
        assert float(updated["total_amount"]) == pytest.approx(3000.0)

    def test_patch_payment_not_found_returns_404(self, app_client: TestClient):
        resp = app_client.patch(
            f"/api/loan-payments/{uuid.uuid4()}",
            json={"status": "PAID"},
        )
        assert resp.status_code == 404

    def test_patch_payment_invalid_status_returns_422(self, app_client: TestClient):
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id),
        ).json()
        resp = app_client.patch(
            f"/api/loan-payments/{created['id']}",
            json={"status": "INVALID"},
        )
        assert resp.status_code == 422

    # --- put ---

    def test_put_payment_returns_200(self, app_client: TestClient):
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id, status="PENDING"),
        ).json()
        resp = app_client.put(
            f"/api/loan-payments/{created['id']}",
            json=_payment_payload(self.loan_app_id, status="PAID"),
        )
        assert resp.status_code == 200

    def test_put_payment_replaces_fields(self, app_client: TestClient):
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(
                self.loan_app_id,
                borrower_name="Old Name",
                status="PENDING",
            ),
        ).json()
        updated = app_client.put(
            f"/api/loan-payments/{created['id']}",
            json=_payment_payload(
                self.loan_app_id,
                borrower_name="New Name",
                status="PAID",
            ),
        ).json()
        assert updated["borrower_name"] == "New Name"
        assert updated["status"] == "PAID"

    def test_put_payment_not_found_returns_404(self, app_client: TestClient):
        resp = app_client.put(
            f"/api/loan-payments/{uuid.uuid4()}",
            json=_payment_payload(self.loan_app_id),
        )
        assert resp.status_code == 404

    # --- delete ---

    def test_delete_payment_returns_204(self, app_client: TestClient):
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id),
        ).json()
        resp = app_client.delete(f"/api/loan-payments/{created['id']}")
        assert resp.status_code == 204

    def test_deleted_payment_not_retrievable(self, app_client: TestClient):
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id),
        ).json()
        app_client.delete(f"/api/loan-payments/{created['id']}")
        resp = app_client.get(f"/api/loan-payments/{created['id']}")
        assert resp.status_code == 404

    def test_delete_payment_not_found_returns_404(self, app_client: TestClient):
        resp = app_client.delete(f"/api/loan-payments/{uuid.uuid4()}")
        assert resp.status_code == 404

    # --- overdue ---

    def test_overdue_endpoint_returns_200(self, app_client: TestClient):
        resp = app_client.get("/api/loan-payments/overdue")
        assert resp.status_code == 200

    def test_overdue_returns_list(self, app_client: TestClient):
        data = app_client.get("/api/loan-payments/overdue").json()
        assert isinstance(data, list)

    def test_overdue_detected_for_past_pending(self, app_client: TestClient):
        past = str(date.today() - timedelta(days=15))
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(
                self.loan_app_id, status="PENDING", due_date=past
            ),
        ).json()
        data = app_client.get("/api/loan-payments/overdue").json()
        ids = [p["id"] for p in data]
        assert created["id"] in ids

    def test_overdue_does_not_include_paid(self, app_client: TestClient):
        past = str(date.today() - timedelta(days=15))
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(
                self.loan_app_id, status="PAID", due_date=past
            ),
        ).json()
        data = app_client.get("/api/loan-payments/overdue").json()
        ids = [p["id"] for p in data]
        assert created["id"] not in ids

    # --- summary ---

    def test_summary_returns_200(self, app_client: TestClient):
        resp = app_client.get(
            f"/api/loan-payments/summary/{self.loan_app_id}"
        )
        assert resp.status_code == 200

    def test_summary_has_required_fields(self, app_client: TestClient):
        data = app_client.get(
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

    def test_summary_counts_paid_payments(self, app_client: TestClient):
        app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id, status="PAID"),
        )
        data = app_client.get(
            f"/api/loan-payments/summary/{self.loan_app_id}"
        ).json()
        assert data["paid_count"] >= 1

    def test_summary_counts_pending_payments(self, app_client: TestClient):
        app_client.post(
            "/api/loan-payments",
            json=_payment_payload(self.loan_app_id, status="PENDING"),
        )
        data = app_client.get(
            f"/api/loan-payments/summary/{self.loan_app_id}"
        ).json()
        assert data["pending_count"] >= 1

    # --- full lifecycle ---

    def test_full_lifecycle(self, app_client: TestClient):
        """Create → Read → Patch → List → Delete — all steps pass."""
        # Create
        created = app_client.post(
            "/api/loan-payments",
            json=_payment_payload(
                self.loan_app_id,
                borrower_name="Lifecycle User",
                status="PENDING",
                total_amount="1000.00",
            ),
        ).json()
        pid = created["id"]

        # Read
        fetched = app_client.get(f"/api/loan-payments/{pid}").json()
        assert fetched["borrower_name"] == "Lifecycle User"

        # Patch
        patched = app_client.patch(
            f"/api/loan-payments/{pid}",
            json={"status": "PAID", "paid_date": str(date.today())},
        ).json()
        assert patched["status"] == "PAID"

        # List
        listing = app_client.get(
            f"/api/loan-payments?loan_application_id={self.loan_app_id}"
        ).json()
        assert any(p["id"] == pid for p in listing)

        # Delete
        del_resp = app_client.delete(f"/api/loan-payments/{pid}")
        assert del_resp.status_code == 204

        # Confirm gone
        gone = app_client.get(f"/api/loan-payments/{pid}")
        assert gone.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# Cross-service interaction tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCrossServiceInteractions:
    """Verify multiple services operate correctly within a single in-process run."""

    def test_all_three_service_prefixes_respond(self, app_client: TestClient):
        for endpoint in ["/api/otp-codes", "/api/notifications", "/api/loan-payments"]:
            resp = app_client.get(endpoint)
            assert resp.status_code == 200, f"{endpoint} returned {resp.status_code}"

    def test_creating_otp_does_not_affect_notifications(self, app_client: TestClient, db_session):
        before = len(app_client.get("/api/notifications").json())
        _insert_otp(db_session, email="cross@example.com")
        after = len(app_client.get("/api/notifications").json())
        assert after == before

    def test_openapi_schema_is_accessible(self, app_client: TestClient):
        resp = app_client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "paths" in schema

    def test_openapi_includes_all_route_prefixes(self, app_client: TestClient):
        schema = app_client.get("/openapi.json").json()
        paths = schema["paths"]
        assert any(p.startswith("/api/otp-codes") for p in paths)
        assert any(p.startswith("/api/auth") for p in paths)
        assert any(p.startswith("/api/notifications") for p in paths)
        assert any(p.startswith("/api/loan-payments") for p in paths)

    def test_docs_endpoint_accessible(self, app_client: TestClient):
        resp = app_client.get("/docs")
        assert resp.status_code == 200

    def test_redoc_endpoint_accessible(self, app_client: TestClient):
        resp = app_client.get("/redoc")
        assert resp.status_code == 200
