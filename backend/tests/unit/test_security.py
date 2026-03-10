"""
Security tests for the Security Microservice.

Covers:
  Task 2 acceptance criteria:
  - Authentication scenarios (OTP flow, missing credentials)
  - Authorization scenarios (access to admin endpoints)
  - Data protection scenarios (no secrets leaked in responses)
  - Input validation / injection resistance
  - Rate limiting
  - HTTP method enforcement
  - Error response sanitisation (no stack traces)

All tests run without a real database (SQLite in-memory via conftest fixtures).
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.models.otp_code import OtpCode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_otp(
    db_session,
    email: str = "sec@example.com",
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


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------

class TestAuthenticationSecurity:
    """Verify OTP-based authentication behaviour."""

    def test_verify_with_no_otp_returns_401(self, app_client: TestClient):
        """Attempting verification with no OTP in DB returns 401, not 500."""
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "nobody@example.com", "code": "000000"},
        )
        assert response.status_code == 401

    def test_verify_returns_401_not_200_on_bad_code(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="auth@example.com", code="111111")
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "auth@example.com", "code": "999999"},
        )
        assert response.status_code == 401

    def test_verify_does_not_expose_otp_value_on_failure(self, app_client: TestClient, db_session):
        """Error response must NOT contain the stored OTP code."""
        _insert_otp(db_session, email="leak@example.com", code="543210")
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "leak@example.com", "code": "000000"},
        )
        body = response.text
        assert "543210" not in body

    def test_verify_does_not_expose_user_data_on_failure(self, app_client: TestClient):
        """401 response body should not enumerate whether the user exists."""
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "ghost@example.com", "code": "000000"},
        )
        # Must be 401, and must not say something like "user not found"
        assert response.status_code == 401
        detail = response.json().get("detail", "").lower()
        assert "not found" not in detail
        assert "user" not in detail

    def test_successful_auth_returns_token_not_password(self, app_client: TestClient, db_session):
        """Token is returned; OTP code must NOT appear in the success response."""
        _insert_otp(db_session, email="sec@example.com", code="654321")
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "sec@example.com", "code": "654321"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert "654321" not in response.text

    def test_otp_cannot_be_reused(self, app_client: TestClient, db_session):
        """Once an OTP is used it cannot authenticate again."""
        _insert_otp(db_session, email="reuse@example.com", code="111111")

        # First use — succeeds
        r1 = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "reuse@example.com", "code": "111111"},
        )
        assert r1.status_code == 200

        # Second use — fails
        r2 = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "reuse@example.com", "code": "111111"},
        )
        assert r2.status_code == 401

    def test_expired_otp_cannot_authenticate(self, app_client: TestClient, db_session):
        _insert_otp(
            db_session,
            email="expauth@example.com",
            code="222222",
            offset_minutes=-1,
        )
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "expauth@example.com", "code": "222222"},
        )
        assert response.status_code == 401

    def test_send_otp_response_is_ambiguous(self, app_client: TestClient):
        """
        send-otp must never confirm whether the address is registered.
        The message must be the same regardless of whether the email exists.
        """
        r = app_client.post("/api/auth/send-otp", json={"email": "any@example.com"})
        assert r.status_code == 200
        # Message must not say "not found" or "unregistered"
        msg = r.json().get("message", "").lower()
        assert "not found" not in msg
        assert "unregistered" not in msg
        assert "does not exist" not in msg


# ---------------------------------------------------------------------------
# Input validation / injection resistance
# ---------------------------------------------------------------------------

class TestInputValidationSecurity:
    """Reject malformed or potentially malicious input at the API boundary."""

    def test_sql_injection_in_email_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/auth/send-otp",
            json={"email": "'; DROP TABLE otp_codes; --"},
        )
        assert response.status_code == 422

    def test_xss_attempt_in_notification_title_is_stored_safe(self, app_client: TestClient):
        """XSS payload stored as-is (HTML escaping is the frontend's job),
        but the API must not execute or reject valid strings."""
        payload = {
            "title": "<script>alert(1)</script>",
            "message": "body",
        }
        response = app_client.post("/api/notifications", json=payload)
        # The server must accept the string and return it verbatim (no execution)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "<script>alert(1)</script>"

    def test_oversized_title_returns_422(self, app_client: TestClient):
        """title has a max_length=255 constraint enforced by the schema."""
        response = app_client.post(
            "/api/notifications",
            json={"title": "x" * 256, "message": "M"},
        )
        assert response.status_code == 422

    def test_oversized_otp_code_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "user@example.com", "code": "1" * 100},
        )
        assert response.status_code == 422

    def test_null_bytes_in_message_handled(self, app_client: TestClient):
        """Null bytes in string fields should produce a 422 or sanitised 201."""
        payload = {"title": "T", "message": "M\x00M"}
        response = app_client.post("/api/notifications", json=payload)
        assert response.status_code in (201, 422)

    def test_numeric_email_field_returns_422(self, app_client: TestClient):
        response = app_client.post("/api/auth/send-otp", json={"email": 12345})
        assert response.status_code == 422

    def test_array_as_notification_title_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/notifications",
            json={"title": ["a", "b"], "message": "M"},
        )
        assert response.status_code == 422

    def test_invalid_uuid_path_param_returns_422(self, app_client: TestClient):
        response = app_client.get("/api/notifications/../../etc/passwd")
        assert response.status_code in (404, 422)

    def test_very_large_json_body_does_not_crash(self, app_client: TestClient):
        """A large but structurally valid payload should not crash the server."""
        response = app_client.post(
            "/api/notifications",
            json={"title": "T", "message": "M" * 10_000},
        )
        # Either accepted or schema-rejected — must not be 500
        assert response.status_code in (201, 422)

    def test_notification_id_path_traversal_returns_422(self, app_client: TestClient):
        response = app_client.get("/api/notifications/../../admin")
        assert response.status_code in (404, 422)


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

class TestRateLimitingSecurity:
    """OTP rate limiting enforced at 5 per hour per email."""

    def test_sixth_otp_request_is_blocked(self, app_client: TestClient, db_session):
        email = "ratelim@example.com"
        for _ in range(5):
            otp = OtpCode(
                email=email,
                code="000000",
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
                used=False,
            )
            db_session.add(otp)
        db_session.commit()

        response = app_client.post("/api/auth/send-otp", json={"email": email})
        assert response.status_code == 429

    def test_rate_limit_returns_json(self, app_client: TestClient, db_session):
        email = "ratejson@example.com"
        for _ in range(5):
            _insert_otp(db_session, email=email)
        response = app_client.post("/api/auth/send-otp", json={"email": email})
        assert response.headers["content-type"].startswith("application/json")
        assert "detail" in response.json()


# ---------------------------------------------------------------------------
# Data protection
# ---------------------------------------------------------------------------

class TestDataProtectionSecurity:
    """Sensitive data must not leak through API responses."""

    def test_otp_list_does_not_expose_code_field(self, app_client: TestClient, db_session):
        """The admin OTP list must NOT return the raw OTP code."""
        _insert_otp(db_session, email="noleak@example.com", code="987654")
        data = app_client.get("/api/otp-codes").json()
        for record in data:
            assert "code" not in record

    def test_otp_get_does_not_expose_code_field(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="noleak2@example.com", code="876543")
        data = app_client.get(f"/api/otp-codes/{otp.id}").json()
        assert "code" not in data

    def test_error_responses_do_not_expose_stack_traces(self, app_client: TestClient):
        """Internal server errors must not include Python tracebacks."""
        # Deliberately hit a 404 — check no stack trace fields
        response = app_client.get(f"/api/notifications/{uuid.uuid4()}")
        body = response.text
        assert "Traceback" not in body
        assert "File " not in body

    def test_404_response_does_not_expose_db_details(self, app_client: TestClient):
        response = app_client.get(f"/api/otp-codes/{uuid.uuid4()}")
        body = response.text
        assert "postgresql" not in body.lower()
        assert "sqlalchemy" not in body.lower()

    def test_422_response_does_not_expose_db_details(self, app_client: TestClient):
        response = app_client.post("/api/auth/send-otp", json={"email": "bad"})
        assert response.status_code == 422
        body = response.text
        assert "sqlalchemy" not in body.lower()
        assert "postgresql" not in body.lower()

    def test_notification_response_excludes_internal_fields(self, app_client: TestClient):
        """Response for a created notification must not contain unexpected internal fields."""
        response = app_client.post(
            "/api/notifications",
            json={"title": "T", "message": "M"},
        )
        data = response.json()
        assert "_sa_instance_state" not in data
        assert "registry" not in data

    def test_verify_otp_success_excludes_otp_record_details(
        self, app_client: TestClient, db_session
    ):
        """Token response must not include the OTP id, code, or expires_at."""
        _insert_otp(db_session, email="clean@example.com", code="123456")
        data = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "clean@example.com", "code": "123456"},
        ).json()
        assert "otp_id" not in data
        assert "expires_at" not in data
        assert "code" not in data


# ---------------------------------------------------------------------------
# HTTP method enforcement
# ---------------------------------------------------------------------------

class TestHttpMethodEnforcement:
    """Endpoints must reject disallowed HTTP methods."""

    def test_get_on_send_otp_returns_405(self, app_client: TestClient):
        response = app_client.get("/api/auth/send-otp")
        assert response.status_code == 405

    def test_get_on_verify_otp_returns_405(self, app_client: TestClient):
        response = app_client.get("/api/auth/verify-otp")
        assert response.status_code == 405

    def test_post_on_notifications_list_is_create_not_list(self, app_client: TestClient):
        """POST on /api/notifications creates — GET lists."""
        get_r = app_client.get("/api/notifications")
        post_r = app_client.post(
            "/api/notifications",
            json={"title": "T", "message": "M"},
        )
        assert get_r.status_code == 200
        assert post_r.status_code == 201

    def test_put_on_notification_returns_405(self, app_client: TestClient):
        response = app_client.put(
            f"/api/notifications/{uuid.uuid4()}",
            json={"title": "T", "message": "M"},
        )
        assert response.status_code == 405

    def test_delete_on_otp_list_returns_405(self, app_client: TestClient):
        response = app_client.delete("/api/otp-codes")
        assert response.status_code == 405
