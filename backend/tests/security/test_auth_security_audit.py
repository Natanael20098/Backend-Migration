"""
Security Audit — Authentication Module
=======================================

Automated security tests aligned with OWASP Top 10 categories.
All tests execute using pytest against the FastAPI application via
TestClient (in-memory SQLite — no Docker required).

OWASP categories covered
────────────────────────
  A01 Broken Access Control
      - Disallowed HTTP methods enforced (405)
      - Admin OTP list does not expose raw codes
      - Path-traversal attempts rejected

  A02 Cryptographic Failures
      - OTP codes never leak in API responses
      - Token does not expose internal OTP data
      - DB connection strings never appear in responses

  A03 Injection
      - SQL injection strings in email field → 422
      - Null bytes in string fields handled gracefully
      - Oversized inputs rejected at schema boundary

  A04 Insecure Design
      - OTP is single-use (can't replay)
      - Expired OTPs rejected
      - Rate limiting enforced (429 after threshold)

  A05 Security Misconfiguration
      - No stack traces in error responses
      - No SQLAlchemy details in 404/422 responses
      - Error messages do not enumerate users

  A07 Identification & Authentication Failures
      - Wrong code → 401
      - Missing credentials → 401 / 422
      - Ambiguous send-otp message (no user enumeration)

  A09 Security Logging and Monitoring Failures
      - Module-level: log calls are present (checked via mock)

Run:
    pytest tests/security/ -v
    pytest tests/security/ -v --html=reports/security-audit.html
"""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.models.otp_code import OtpCode


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _insert_otp(
    db_session,
    *,
    email: str = "audit@example.com",
    code: str = "123456",
    used: bool = False,
    offset_minutes: int = 10,
) -> OtpCode:
    expires = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    otp = OtpCode(email=email, code=code, expires_at=expires, used=used)
    db_session.add(otp)
    db_session.commit()
    db_session.refresh(otp)
    return otp


def _verify(client: TestClient, email: str, code: str):
    return client.post(
        "/api/auth/verify-otp", json={"email": email, "code": code}
    )


def _send(client: TestClient, email: str):
    return client.post("/api/auth/send-otp", json={"email": email})


# ─────────────────────────────────────────────────────────────────────────────
# A01 — Broken Access Control
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.security
class TestA01BrokenAccessControl:
    """OWASP A01: Broken Access Control"""

    def test_get_send_otp_is_not_allowed(self, app_client: TestClient):
        """send-otp must only accept POST — GET should be 405."""
        assert app_client.get("/api/auth/send-otp").status_code == 405

    def test_get_verify_otp_is_not_allowed(self, app_client: TestClient):
        """verify-otp must only accept POST."""
        assert app_client.get("/api/auth/verify-otp").status_code == 405

    def test_put_send_otp_is_not_allowed(self, app_client: TestClient):
        assert app_client.put("/api/auth/send-otp", json={}).status_code == 405

    def test_delete_send_otp_is_not_allowed(self, app_client: TestClient):
        assert app_client.delete("/api/auth/send-otp").status_code == 405

    def test_delete_otp_list_is_not_allowed(self, app_client: TestClient):
        """Bulk delete of OTP records must be forbidden."""
        assert app_client.delete("/api/otp-codes").status_code == 405

    def test_put_notification_not_allowed(self, app_client: TestClient):
        resp = app_client.put(
            f"/api/notifications/{uuid.uuid4()}",
            json={"title": "T", "message": "M"},
        )
        assert resp.status_code == 405

    def test_path_traversal_on_notifications(self, app_client: TestClient):
        resp = app_client.get("/api/notifications/../../etc/passwd")
        assert resp.status_code in (404, 422)

    def test_path_traversal_on_otp_codes(self, app_client: TestClient):
        resp = app_client.get("/api/otp-codes/../../admin")
        assert resp.status_code in (404, 422)

    def test_random_uuid_notification_returns_404_not_200(self, app_client: TestClient):
        resp = app_client.get(f"/api/notifications/{uuid.uuid4()}")
        assert resp.status_code == 404

    def test_random_uuid_otp_returns_404_not_200(self, app_client: TestClient):
        resp = app_client.get(f"/api/otp-codes/{uuid.uuid4()}")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# A02 — Cryptographic Failures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.security
class TestA02CryptographicFailures:
    """OWASP A02: Cryptographic Failures — sensitive data must not be exposed."""

    def test_otp_code_not_in_list_response(self, app_client: TestClient, db_session):
        """GET /api/otp-codes must never return the raw `code` field."""
        _insert_otp(db_session, email="nocrypt@example.com", code="112233")
        records = app_client.get("/api/otp-codes").json()
        for record in records:
            assert "code" not in record, "Raw OTP code leaked in list endpoint"

    def test_otp_code_not_in_get_by_id_response(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="getleak@example.com", code="445566")
        data = app_client.get(f"/api/otp-codes/{otp.id}").json()
        assert "code" not in data

    def test_otp_code_not_in_verify_success_response(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="verifyleak@example.com", code="778899")
        data = _verify(app_client, "verifyleak@example.com", "778899").json()
        assert "778899" not in str(data)
        assert "code" not in data

    def test_verify_success_response_has_no_otp_internals(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="nointernal@example.com", code="654321")
        data = _verify(app_client, "nointernal@example.com", "654321").json()
        assert "otp_id" not in data
        assert "expires_at" not in data
        assert "code" not in data

    def test_token_returned_on_success(self, app_client: TestClient, db_session):
        """Token field must be present and non-trivial on success."""
        _insert_otp(db_session, email="tokencheck@example.com", code="111222")
        data = _verify(app_client, "tokencheck@example.com", "111222").json()
        assert "token" in data
        assert len(data["token"]) >= 32

    def test_db_url_not_in_error_responses(self, app_client: TestClient):
        """Database connection string must never appear in API responses."""
        resp = app_client.get(f"/api/otp-codes/{uuid.uuid4()}")
        body = resp.text.lower()
        assert "postgresql" not in body
        assert "sqlalchemy" not in body
        assert "chiron" not in body  # DB name

    def test_notification_response_no_sa_instance_state(self, app_client: TestClient):
        resp = app_client.post(
            "/api/notifications", json={"title": "T", "message": "M"}
        )
        data = resp.json()
        assert "_sa_instance_state" not in data

    def test_422_response_no_db_details(self, app_client: TestClient):
        resp = app_client.post("/api/auth/send-otp", json={"email": "bad-email"})
        assert resp.status_code == 422
        assert "sqlalchemy" not in resp.text.lower()
        assert "postgresql" not in resp.text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# A03 — Injection
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.security
class TestA03Injection:
    """OWASP A03: Injection — malicious input must be rejected or sanitised."""

    def test_sql_injection_in_send_otp_email(self, app_client: TestClient):
        resp = _send(app_client, "'; DROP TABLE otp_codes; --")
        assert resp.status_code == 422

    def test_sql_injection_classic_in_email(self, app_client: TestClient):
        resp = _send(app_client, "1' OR '1'='1")
        assert resp.status_code == 422

    def test_html_injection_in_notification_title_stored_verbatim(
        self, app_client: TestClient
    ):
        """XSS payload stored as-is — the server must not execute it."""
        resp = app_client.post(
            "/api/notifications",
            json={"title": "<script>alert('xss')</script>", "message": "M"},
        )
        assert resp.status_code == 201
        assert resp.json()["title"] == "<script>alert('xss')</script>"

    def test_null_bytes_in_notification_message(self, app_client: TestClient):
        resp = app_client.post(
            "/api/notifications", json={"title": "T", "message": "M\x00M"}
        )
        assert resp.status_code in (201, 422)

    def test_unicode_control_chars_in_title(self, app_client: TestClient):
        resp = app_client.post(
            "/api/notifications",
            json={"title": "Title\u0000End", "message": "M"},
        )
        assert resp.status_code in (201, 422)

    def test_template_injection_attempt_in_message(self, app_client: TestClient):
        """Server-side template injection patterns must not crash the server."""
        resp = app_client.post(
            "/api/notifications",
            json={"title": "T", "message": "{{7*7}} ${7*7} #{7*7}"},
        )
        assert resp.status_code in (201, 422)
        if resp.status_code == 201:
            # Value should be stored verbatim, not evaluated
            assert "49" not in resp.json()["message"]

    def test_oversized_otp_code_rejected(self, app_client: TestClient):
        resp = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "user@example.com", "code": "1" * 100},
        )
        assert resp.status_code == 422

    def test_oversized_title_rejected(self, app_client: TestClient):
        resp = app_client.post(
            "/api/notifications",
            json={"title": "x" * 256, "message": "M"},
        )
        assert resp.status_code == 422

    def test_very_large_json_payload_does_not_crash(self, app_client: TestClient):
        resp = app_client.post(
            "/api/notifications",
            json={"title": "T", "message": "M" * 50_000},
        )
        assert resp.status_code in (201, 422)
        # Must never be a 5xx
        assert resp.status_code < 500

    def test_numeric_type_for_email_returns_422(self, app_client: TestClient):
        resp = app_client.post("/api/auth/send-otp", json={"email": 12345})
        assert resp.status_code == 422

    def test_array_type_for_notification_title_returns_422(
        self, app_client: TestClient
    ):
        resp = app_client.post(
            "/api/notifications", json={"title": ["a", "b"], "message": "M"}
        )
        assert resp.status_code == 422

    def test_boolean_type_for_email_returns_422(self, app_client: TestClient):
        resp = app_client.post("/api/auth/send-otp", json={"email": True})
        assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# A04 — Insecure Design
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.security
class TestA04InsecureDesign:
    """OWASP A04: Insecure Design — authentication design must be sound."""

    def test_otp_is_single_use(self, app_client: TestClient, db_session):
        """Once an OTP is verified, replaying it must fail."""
        _insert_otp(db_session, email="single@example.com", code="100200")
        r1 = _verify(app_client, "single@example.com", "100200")
        assert r1.status_code == 200
        r2 = _verify(app_client, "single@example.com", "100200")
        assert r2.status_code == 401

    def test_used_otp_marked_in_db(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="dbmark@example.com", code="300400")
        _verify(app_client, "dbmark@example.com", "300400")
        db_session.refresh(otp)
        assert otp.used is True

    def test_expired_otp_rejected(self, app_client: TestClient, db_session):
        _insert_otp(
            db_session, email="exp@example.com", code="500600", offset_minutes=-1
        )
        resp = _verify(app_client, "exp@example.com", "500600")
        assert resp.status_code == 401

    def test_future_otp_works_when_not_expired(self, app_client: TestClient, db_session):
        _insert_otp(
            db_session, email="fresh@example.com", code="700800", offset_minutes=5
        )
        resp = _verify(app_client, "fresh@example.com", "700800")
        assert resp.status_code == 200

    def test_wrong_email_with_valid_code_fails(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="real@example.com", code="111111")
        resp = _verify(app_client, "wrong@example.com", "111111")
        assert resp.status_code == 401

    def test_wrong_code_with_valid_email_fails(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="coded@example.com", code="222222")
        resp = _verify(app_client, "coded@example.com", "333333")
        assert resp.status_code == 401

    def test_missing_email_body_returns_422(self, app_client: TestClient):
        resp = app_client.post("/api/auth/verify-otp", json={"code": "123456"})
        assert resp.status_code == 422

    def test_missing_code_body_returns_422(self, app_client: TestClient):
        resp = app_client.post(
            "/api/auth/verify-otp", json={"email": "x@example.com"}
        )
        assert resp.status_code == 422

    def test_empty_body_verify_otp_returns_422(self, app_client: TestClient):
        resp = app_client.post("/api/auth/verify-otp", json={})
        assert resp.status_code == 422

    def test_empty_body_send_otp_returns_422(self, app_client: TestClient):
        resp = app_client.post("/api/auth/send-otp", json={})
        assert resp.status_code == 422

    def test_otp_code_must_be_six_digits(self, app_client: TestClient):
        """5-digit code must fail schema validation."""
        resp = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "x@example.com", "code": "12345"},
        )
        assert resp.status_code == 422

    def test_non_numeric_otp_code_rejected(self, app_client: TestClient):
        resp = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "x@example.com", "code": "abcdef"},
        )
        assert resp.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# A05 — Security Misconfiguration
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.security
class TestA05SecurityMisconfiguration:
    """OWASP A05: Security Misconfiguration — server must not leak internals."""

    def test_404_has_no_python_traceback(self, app_client: TestClient):
        resp = app_client.get(f"/api/notifications/{uuid.uuid4()}")
        assert "Traceback" not in resp.text
        assert "File " not in resp.text

    def test_422_has_no_python_traceback(self, app_client: TestClient):
        resp = app_client.post("/api/auth/send-otp", json={"email": "bad"})
        assert "Traceback" not in resp.text
        assert "File " not in resp.text

    def test_nonexistent_route_returns_404_not_500(self, app_client: TestClient):
        resp = app_client.get("/this/does/not/exist")
        assert resp.status_code == 404

    def test_404_no_stack_trace(self, app_client: TestClient):
        resp = app_client.get("/nonexistent-endpoint")
        assert "Traceback" not in resp.text

    def test_db_connection_details_absent_from_404(self, app_client: TestClient):
        resp = app_client.get(f"/api/otp-codes/{uuid.uuid4()}")
        body = resp.text.lower()
        assert "postgresql" not in body
        assert "sqlalchemy" not in body

    def test_db_connection_details_absent_from_422(self, app_client: TestClient):
        resp = app_client.post("/api/auth/send-otp", json={"email": "bad"})
        body = resp.text.lower()
        assert "postgresql" not in body
        assert "sqlalchemy" not in body

    def test_internal_server_error_not_returned_for_valid_input(
        self, app_client: TestClient
    ):
        resp = app_client.post(
            "/api/auth/send-otp", json={"email": "valid@example.com"}
        )
        assert resp.status_code < 500

    def test_cors_headers_present_or_not_crashing(self, app_client: TestClient):
        """The server must return a valid response to an OPTIONS request."""
        resp = app_client.options("/api/auth/send-otp")
        # 200 or 405 are both acceptable — must not be 500
        assert resp.status_code < 500


# ─────────────────────────────────────────────────────────────────────────────
# A07 — Identification and Authentication Failures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.security
class TestA07IdentificationAndAuthentication:
    """OWASP A07: Identification and Authentication Failures."""

    def test_no_otp_returns_401_not_200(self, app_client: TestClient):
        resp = _verify(app_client, "nobody@example.com", "000000")
        assert resp.status_code == 401

    def test_verify_failure_detail_is_ambiguous(self, app_client: TestClient):
        """401 must not reveal whether the user exists."""
        resp = _verify(app_client, "ghost@example.com", "000000")
        detail = resp.json().get("detail", "").lower()
        assert "not found" not in detail
        assert "user" not in detail
        assert "does not exist" not in detail

    def test_send_otp_message_is_ambiguous(self, app_client: TestClient):
        resp = _send(app_client, "any@example.com")
        assert resp.status_code == 200
        msg = resp.json().get("message", "").lower()
        assert "not found" not in msg
        assert "unregistered" not in msg
        assert "does not exist" not in msg

    def test_wrong_password_rate_limit_429(self, app_client: TestClient, db_session):
        """send-otp rate-limit: 6th request within the hour window → 429."""
        email = f"rl_{uuid.uuid4().hex[:6]}@example.com"
        for _ in range(5):
            _insert_otp(db_session, email=email, code="000000")
        resp = _send(app_client, email)
        assert resp.status_code == 429

    def test_rate_limit_response_is_json(self, app_client: TestClient, db_session):
        email = f"rljson_{uuid.uuid4().hex[:6]}@example.com"
        for _ in range(5):
            _insert_otp(db_session, email=email, code="000000")
        resp = _send(app_client, email)
        assert resp.headers["content-type"].startswith("application/json")
        assert "detail" in resp.json()

    def test_rate_limit_detail_not_exposing_count(self, app_client: TestClient, db_session):
        """Rate-limit response must not expose the exact count of requests."""
        email = f"rlcount_{uuid.uuid4().hex[:6]}@example.com"
        for _ in range(5):
            _insert_otp(db_session, email=email, code="000000")
        resp = _send(app_client, email)
        detail = resp.json().get("detail", "").lower()
        # Should not say "5 requests found" or similar
        assert "5 request" not in detail

    def test_different_emails_have_independent_rate_limits(
        self, app_client: TestClient, db_session
    ):
        email1 = f"rl1_{uuid.uuid4().hex[:6]}@example.com"
        email2 = f"rl2_{uuid.uuid4().hex[:6]}@example.com"
        for _ in range(5):
            _insert_otp(db_session, email=email1, code="000000")
        # email2 must NOT be rate-limited
        resp = _send(app_client, email2)
        assert resp.status_code == 200

    def test_pre_used_otp_cannot_authenticate(self, app_client: TestClient, db_session):
        _insert_otp(
            db_session, email="preused@example.com", code="888999", used=True
        )
        resp = _verify(app_client, "preused@example.com", "888999")
        assert resp.status_code == 401

    def test_expired_otp_returns_401_not_403(self, app_client: TestClient, db_session):
        _insert_otp(
            db_session,
            email="expauth2@example.com",
            code="444555",
            offset_minutes=-60,
        )
        resp = _verify(app_client, "expauth2@example.com", "444555")
        assert resp.status_code == 401  # not 403 — no resource to be forbidden from

    def test_email_case_insensitive_lookup(self, app_client: TestClient, db_session):
        """OTP lookup must be case-insensitive for email."""
        _insert_otp(db_session, email="casetest@example.com", code="123456")
        resp = _verify(app_client, "CASETEST@EXAMPLE.COM", "123456")
        # Should succeed — email is normalised to lowercase in the router
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# A09 — Security Logging and Monitoring
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.security
class TestA09SecurityLoggingAndMonitoring:
    """OWASP A09: Security Logging and Monitoring."""

    def test_failed_auth_is_logged(self, app_client: TestClient):
        """A warning must be logged when OTP verification fails."""
        import logging
        with patch.object(
            logging.getLogger("app.routers.otp_codes"), "warning"
        ) as mock_warn:
            _verify(app_client, "log_fail@example.com", "000000")
            mock_warn.assert_called()

    def test_successful_auth_is_logged(self, app_client: TestClient, db_session):
        """An info-level log must be emitted on successful authentication."""
        import logging
        _insert_otp(db_session, email="log_ok@example.com", code="111111")
        with patch.object(
            logging.getLogger("app.routers.otp_codes"), "info"
        ) as mock_info:
            _verify(app_client, "log_ok@example.com", "111111")
            mock_info.assert_called()

    def test_rate_limit_exceeded_is_logged(self, app_client: TestClient, db_session):
        """Rate-limit violation must emit a warning log."""
        import logging
        email = f"rllog_{uuid.uuid4().hex[:6]}@example.com"
        for _ in range(5):
            _insert_otp(db_session, email=email, code="000000")
        with patch.object(
            logging.getLogger("app.routers.otp_codes"), "warning"
        ) as mock_warn:
            _send(app_client, email)
            mock_warn.assert_called()

    def test_otp_creation_is_logged(self, app_client: TestClient):
        """send-otp success must emit an info-level log."""
        import logging
        with patch.object(
            logging.getLogger("app.routers.otp_codes"), "info"
        ) as mock_info:
            _send(app_client, f"newlog_{uuid.uuid4().hex[:6]}@example.com")
            mock_info.assert_called()

    def test_notification_creation_is_logged(self, app_client: TestClient):
        import logging
        with patch.object(
            logging.getLogger("app.routers.notifications"), "info"
        ) as mock_info:
            app_client.post(
                "/api/notifications", json={"title": "T", "message": "M"}
            )
            mock_info.assert_called()

    def test_otp_deletion_is_logged(self, app_client: TestClient, db_session):
        import logging
        otp = _insert_otp(db_session, email="dellog@example.com")
        with patch.object(
            logging.getLogger("app.routers.otp_codes"), "info"
        ) as mock_info:
            app_client.delete(f"/api/otp-codes/{otp.id}")
            mock_info.assert_called()
