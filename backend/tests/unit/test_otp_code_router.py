"""
Unit tests for app/routers/otp_codes.py

Covers:
  - POST  /api/auth/send-otp    (generate & store OTP)
  - POST  /api/auth/verify-otp  (verify OTP, return token)
  - GET   /api/otp-codes        (admin list)
  - GET   /api/otp-codes/{id}   (admin get)
  - DELETE /api/otp-codes/{id}  (admin delete)

  Edge cases:
  - Invalid payloads (bad email, bad code format)
  - Rate limiting (429 after 5 requests per hour)
  - Expired OTP → 401
  - Already-used OTP → 401
  - Non-existent resource → 404
  - Successful authentication returns token
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.models.otp_code import OtpCode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _send_otp(client: TestClient, email: str = "user@example.com") -> dict:
    response = client.post("/api/auth/send-otp", json={"email": email})
    assert response.status_code == 200, response.text
    return response.json()


def _get_otp_code(db_session, email: str) -> OtpCode:
    """Retrieve the most recently created OTP for the given email."""
    return (
        db_session.query(OtpCode)
        .filter(OtpCode.email == email)
        .order_by(OtpCode.created_at.desc())
        .first()
    )


def _insert_otp(
    db_session,
    email: str = "user@example.com",
    code: str = "123456",
    used: bool = False,
    offset_minutes: int = 10,
) -> OtpCode:
    """Insert an OTP row directly for test setup."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=offset_minutes)
    otp = OtpCode(email=email, code=code, expires_at=expires_at, used=used)
    db_session.add(otp)
    db_session.commit()
    db_session.refresh(otp)
    return otp


# ---------------------------------------------------------------------------
# Model unit tests
# ---------------------------------------------------------------------------

class TestOtpCodeModel:
    """ORM model maps to the expected table and columns."""

    def test_tablename(self):
        assert OtpCode.__tablename__ == "otp_codes"

    def test_has_id(self):
        assert hasattr(OtpCode, "id")

    def test_has_email(self):
        assert hasattr(OtpCode, "email")

    def test_has_code(self):
        assert hasattr(OtpCode, "code")

    def test_has_expires_at(self):
        assert hasattr(OtpCode, "expires_at")

    def test_has_used(self):
        assert hasattr(OtpCode, "used")

    def test_has_created_at(self):
        assert hasattr(OtpCode, "created_at")

    def test_db_persistence(self, db_session):
        otp = _insert_otp(db_session)
        fetched = db_session.get(OtpCode, otp.id)
        assert fetched is not None
        assert fetched.email == "user@example.com"
        assert fetched.used is False


# ---------------------------------------------------------------------------
# Schema unit tests
# ---------------------------------------------------------------------------

class TestOtpSchemas:
    """Pydantic schemas validate and reject data."""

    def test_send_otp_request_valid(self):
        from app.schemas.otp_code import SendOtpRequest

        schema = SendOtpRequest(email="a@b.com")
        assert schema.email == "a@b.com"

    def test_send_otp_request_invalid_email(self):
        from pydantic import ValidationError
        from app.schemas.otp_code import SendOtpRequest

        with pytest.raises(ValidationError):
            SendOtpRequest(email="not-an-email")

    def test_verify_otp_request_valid(self):
        from app.schemas.otp_code import VerifyOtpRequest

        schema = VerifyOtpRequest(email="a@b.com", code="123456")
        assert schema.code == "123456"

    def test_verify_otp_request_rejects_non_digit_code(self):
        from pydantic import ValidationError
        from app.schemas.otp_code import VerifyOtpRequest

        with pytest.raises(ValidationError):
            VerifyOtpRequest(email="a@b.com", code="12345a")

    def test_verify_otp_request_rejects_short_code(self):
        from pydantic import ValidationError
        from app.schemas.otp_code import VerifyOtpRequest

        with pytest.raises(ValidationError):
            VerifyOtpRequest(email="a@b.com", code="1234")

    def test_verify_otp_request_rejects_long_code(self):
        from pydantic import ValidationError
        from app.schemas.otp_code import VerifyOtpRequest

        with pytest.raises(ValidationError):
            VerifyOtpRequest(email="a@b.com", code="1234567")


# ---------------------------------------------------------------------------
# POST /api/auth/send-otp
# ---------------------------------------------------------------------------

class TestSendOtp:
    """POST /api/auth/send-otp — OTP generation endpoint."""

    def test_returns_200(self, app_client: TestClient):
        response = app_client.post("/api/auth/send-otp", json={"email": "user@example.com"})
        assert response.status_code == 200

    def test_response_contains_message(self, app_client: TestClient):
        data = _send_otp(app_client)
        assert "message" in data

    def test_response_message_is_ambiguous(self, app_client: TestClient):
        """Security: response should not reveal whether the email exists."""
        data = _send_otp(app_client)
        assert "code has been sent" in data["message"].lower() or "registered" in data["message"].lower()

    def test_otp_is_persisted_in_db(self, app_client: TestClient, db_session):
        _send_otp(app_client, email="db@example.com")
        otp = _get_otp_code(db_session, "db@example.com")
        assert otp is not None
        assert otp.email == "db@example.com"

    def test_otp_code_is_six_digits(self, app_client: TestClient, db_session):
        _send_otp(app_client, email="digits@example.com")
        otp = _get_otp_code(db_session, "digits@example.com")
        assert len(otp.code) == 6
        assert otp.code.isdigit()

    def test_otp_not_used_on_creation(self, app_client: TestClient, db_session):
        _send_otp(app_client, email="used@example.com")
        otp = _get_otp_code(db_session, "used@example.com")
        assert otp.used is False

    def test_otp_expires_in_future(self, app_client: TestClient, db_session):
        _send_otp(app_client, email="exp@example.com")
        otp = _get_otp_code(db_session, "exp@example.com")
        now = datetime.now(timezone.utc)
        # expires_at stored as naive UTC in SQLite; make comparison timezone-safe
        expires = otp.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        assert expires > now

    def test_send_otp_email_normalised_lowercase(self, app_client: TestClient, db_session):
        _send_otp(app_client, email="UPPER@EXAMPLE.COM")
        otp = _get_otp_code(db_session, "upper@example.com")
        assert otp is not None

    def test_invalid_email_returns_422(self, app_client: TestClient):
        response = app_client.post("/api/auth/send-otp", json={"email": "bad-email"})
        assert response.status_code == 422

    def test_missing_email_field_returns_422(self, app_client: TestClient):
        response = app_client.post("/api/auth/send-otp", json={})
        assert response.status_code == 422

    def test_empty_body_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/auth/send-otp",
            content="",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_rate_limit_returns_429(self, app_client: TestClient, db_session):
        """After 5 OTPs in < 1 hour the endpoint returns 429."""
        email = "ratelimit@example.com"
        # Pre-insert 5 recent OTPs directly
        for _ in range(5):
            _insert_otp(db_session, email=email, code="000000")

        response = app_client.post("/api/auth/send-otp", json={"email": email})
        assert response.status_code == 429

    def test_rate_limit_error_detail(self, app_client: TestClient, db_session):
        email = "ratelimit2@example.com"
        for _ in range(5):
            _insert_otp(db_session, email=email, code="000000")

        response = app_client.post("/api/auth/send-otp", json={"email": email})
        assert "too many" in response.json()["detail"].lower()

    def test_otp_dispatch_is_logged(self, app_client: TestClient, caplog):
        with caplog.at_level(logging.INFO, logger="app.routers.otp_codes"):
            _send_otp(app_client, email="log@example.com")
        assert "log@example.com" in caplog.text

    def test_second_send_creates_new_otp(self, app_client: TestClient, db_session):
        email = "multi@example.com"
        _send_otp(app_client, email=email)
        _send_otp(app_client, email=email)
        count = db_session.query(OtpCode).filter(OtpCode.email == email).count()
        assert count == 2


# ---------------------------------------------------------------------------
# POST /api/auth/verify-otp
# ---------------------------------------------------------------------------

class TestVerifyOtp:
    """POST /api/auth/verify-otp — OTP verification endpoint."""

    def test_valid_otp_returns_200(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="verify@example.com", code="654321")
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "verify@example.com", "code": "654321"},
        )
        assert response.status_code == 200

    def test_valid_otp_response_has_token(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="token@example.com", code="111111")
        data = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "token@example.com", "code": "111111"},
        ).json()
        assert "token" in data
        assert len(data["token"]) > 0

    def test_valid_otp_response_has_email(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="email@example.com", code="222222")
        data = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "email@example.com", "code": "222222"},
        ).json()
        assert data["email"] == "email@example.com"

    def test_valid_otp_response_has_expires_in(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="expiry@example.com", code="333333")
        data = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "expiry@example.com", "code": "333333"},
        ).json()
        assert "expires_in" in data
        assert data["expires_in"] == 86400

    def test_valid_otp_is_marked_used(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="mark@example.com", code="444444")
        app_client.post(
            "/api/auth/verify-otp",
            json={"email": "mark@example.com", "code": "444444"},
        )
        db_session.refresh(otp)
        assert otp.used is True

    def test_wrong_code_returns_401(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="wrong@example.com", code="555555")
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "wrong@example.com", "code": "000000"},
        )
        assert response.status_code == 401

    def test_wrong_code_error_detail(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="detail@example.com", code="666666")
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "detail@example.com", "code": "999999"},
        )
        assert "invalid" in response.json()["detail"].lower() or "expired" in response.json()["detail"].lower()

    def test_expired_otp_returns_401(self, app_client: TestClient, db_session):
        _insert_otp(
            db_session,
            email="expired@example.com",
            code="777777",
            offset_minutes=-5,  # already expired
        )
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "expired@example.com", "code": "777777"},
        )
        assert response.status_code == 401

    def test_used_otp_returns_401(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="used@example.com", code="888888", used=True)
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "used@example.com", "code": "888888"},
        )
        assert response.status_code == 401

    def test_unknown_email_returns_401(self, app_client: TestClient):
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "ghost@example.com", "code": "000000"},
        )
        assert response.status_code == 401

    def test_invalid_email_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "not-email", "code": "123456"},
        )
        assert response.status_code == 422

    def test_non_digit_code_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "user@example.com", "code": "12345x"},
        )
        assert response.status_code == 422

    def test_short_code_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "user@example.com", "code": "1234"},
        )
        assert response.status_code == 422

    def test_missing_code_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "user@example.com"},
        )
        assert response.status_code == 422

    def test_missing_email_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"code": "123456"},
        )
        assert response.status_code == 422

    def test_success_logs_authentication(self, app_client: TestClient, db_session, caplog):
        _insert_otp(db_session, email="logauth@example.com", code="123456")
        with caplog.at_level(logging.INFO, logger="app.routers.otp_codes"):
            app_client.post(
                "/api/auth/verify-otp",
                json={"email": "logauth@example.com", "code": "123456"},
            )
        assert "logauth@example.com" in caplog.text

    def test_email_normalised_before_lookup(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="normal@example.com", code="123456")
        response = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "NORMAL@EXAMPLE.COM", "code": "123456"},
        )
        assert response.status_code == 200

    def test_tokens_are_unique_per_request(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="unique1@example.com", code="111111")
        _insert_otp(db_session, email="unique2@example.com", code="222222")
        r1 = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "unique1@example.com", "code": "111111"},
        ).json()
        r2 = app_client.post(
            "/api/auth/verify-otp",
            json={"email": "unique2@example.com", "code": "222222"},
        ).json()
        assert r1["token"] != r2["token"]


# ---------------------------------------------------------------------------
# GET /api/otp-codes  (admin list)
# ---------------------------------------------------------------------------

class TestListOtpCodes:
    """GET /api/otp-codes — admin list endpoint."""

    def test_returns_200(self, app_client: TestClient):
        response = app_client.get("/api/otp-codes")
        assert response.status_code == 200

    def test_returns_list(self, app_client: TestClient):
        assert isinstance(app_client.get("/api/otp-codes").json(), list)

    def test_returns_created_records(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="list1@example.com", code="100001")
        _insert_otp(db_session, email="list2@example.com", code="100002")
        data = app_client.get("/api/otp-codes").json()
        assert len(data) == 2

    def test_filter_by_email(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="filter@example.com", code="200001")
        _insert_otp(db_session, email="other@example.com", code="200002")
        data = app_client.get("/api/otp-codes?email=filter@example.com").json()
        assert len(data) == 1
        assert data[0]["email"] == "filter@example.com"

    def test_filter_by_used_false(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="used1@example.com", code="300001", used=True)
        _insert_otp(db_session, email="used2@example.com", code="300002", used=False)
        data = app_client.get("/api/otp-codes?used=false").json()
        assert all(r["used"] is False for r in data)

    def test_filter_by_used_true(self, app_client: TestClient, db_session):
        _insert_otp(db_session, email="used3@example.com", code="400001", used=True)
        _insert_otp(db_session, email="used4@example.com", code="400002", used=False)
        data = app_client.get("/api/otp-codes?used=true").json()
        assert all(r["used"] is True for r in data)

    def test_response_does_not_expose_raw_code(self, app_client: TestClient, db_session):
        """OtpCodeRead schema should not include the raw code value."""
        _insert_otp(db_session, email="schema@example.com", code="999999")
        data = app_client.get("/api/otp-codes").json()
        assert len(data) > 0
        for record in data:
            assert "code" not in record


# ---------------------------------------------------------------------------
# GET /api/otp-codes/{id}
# ---------------------------------------------------------------------------

class TestGetOtpCode:
    """GET /api/otp-codes/{id} — admin get by ID endpoint."""

    def test_returns_200_for_existing(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="get@example.com", code="111111")
        response = app_client.get(f"/api/otp-codes/{otp.id}")
        assert response.status_code == 200

    def test_returns_correct_record(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="correct@example.com", code="222222")
        data = app_client.get(f"/api/otp-codes/{otp.id}").json()
        assert data["id"] == str(otp.id)
        assert data["email"] == "correct@example.com"

    def test_returns_404_for_nonexistent(self, app_client: TestClient):
        response = app_client.get(f"/api/otp-codes/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_404_detail_message(self, app_client: TestClient):
        response = app_client.get(f"/api/otp-codes/{uuid.uuid4()}")
        assert "not found" in response.json()["detail"].lower()

    def test_invalid_uuid_returns_422(self, app_client: TestClient):
        response = app_client.get("/api/otp-codes/not-a-uuid")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/otp-codes/{id}
# ---------------------------------------------------------------------------

class TestDeleteOtpCode:
    """DELETE /api/otp-codes/{id} — admin delete endpoint."""

    def test_delete_returns_204(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="del@example.com", code="111111")
        response = app_client.delete(f"/api/otp-codes/{otp.id}")
        assert response.status_code == 204

    def test_delete_removes_record(self, app_client: TestClient, db_session):
        otp = _insert_otp(db_session, email="remove@example.com", code="222222")
        app_client.delete(f"/api/otp-codes/{otp.id}")
        response = app_client.get(f"/api/otp-codes/{otp.id}")
        assert response.status_code == 404

    def test_delete_nonexistent_returns_404(self, app_client: TestClient):
        response = app_client.delete(f"/api/otp-codes/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_delete_invalid_uuid_returns_422(self, app_client: TestClient):
        response = app_client.delete("/api/otp-codes/not-a-uuid")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

class TestOtpRouterRegistration:
    """OTP router endpoints are mounted on the FastAPI app."""

    def test_send_otp_route_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/auth/send-otp" in paths

    def test_verify_otp_route_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/auth/verify-otp" in paths

    def test_list_otp_codes_route_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/otp-codes" in paths

    def test_get_otp_code_route_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/otp-codes/{otp_id}" in paths
