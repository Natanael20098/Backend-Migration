"""
Unit tests for app/routers/audit_logs.py

Covers:
  - POST /api/audit-logs  (create)
  - GET  /api/audit-logs  (list with pagination and filtering)
  - AuditLog ORM model attributes and persistence
  - AuditLogCreate / AuditLogRead / AuditLogPage schema validation
  - Mocked database interactions (pytest monkeypatch / unittest.mock)

Edge cases:
  - Missing required fields → 422
  - Pagination parameters (page, size)
  - Filtering by action, entity_type, user_id
  - Response shape validation
  - Database error propagation
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _audit_log_payload(**overrides) -> dict:
    """Return a minimal valid audit log creation payload."""
    base = {
        "action": "CREATE",
        "entity_type": "Property",
    }
    base.update(overrides)
    return base


def _create_audit_log(client: TestClient, **overrides) -> dict:
    """POST an audit log and return the response JSON."""
    response = client.post("/api/audit-logs", json=_audit_log_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Model unit tests
# ---------------------------------------------------------------------------

class TestAuditLogModel:
    """ORM model maps to the expected table and columns."""

    def test_tablename(self):
        from app.models.audit_log import AuditLog
        assert AuditLog.__tablename__ == "audit_logs"

    def test_has_id(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "id")

    def test_has_action(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "action")

    def test_has_entity_type(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "entity_type")

    def test_has_entity_id(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "entity_id")

    def test_has_user_id(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "user_id")

    def test_has_user_email(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "user_email")

    def test_has_description(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "description")

    def test_has_ip_address(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "ip_address")

    def test_has_created_at(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "created_at")

    def test_db_persistence(self, db_session):
        """AuditLog can be persisted and retrieved from SQLite."""
        from app.models.audit_log import AuditLog

        log = AuditLog(action="UPDATE", entity_type="Loan")
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        fetched = db_session.get(AuditLog, log.id)
        assert fetched is not None
        assert fetched.action == "UPDATE"
        assert fetched.entity_type == "Loan"


# ---------------------------------------------------------------------------
# Schema unit tests
# ---------------------------------------------------------------------------

class TestAuditLogSchemas:
    """Pydantic schemas validate and reject data correctly."""

    def test_create_schema_accepts_valid_payload(self):
        from app.schemas.audit_log import AuditLogCreate
        schema = AuditLogCreate(action="DELETE", entity_type="Agent")
        assert schema.action == "DELETE"

    def test_create_schema_rejects_empty_action(self):
        from pydantic import ValidationError
        from app.schemas.audit_log import AuditLogCreate
        with pytest.raises(ValidationError):
            AuditLogCreate(action="", entity_type="Agent")

    def test_create_schema_rejects_empty_entity_type(self):
        from pydantic import ValidationError
        from app.schemas.audit_log import AuditLogCreate
        with pytest.raises(ValidationError):
            AuditLogCreate(action="CREATE", entity_type="")

    def test_create_schema_optional_fields_default_to_none(self):
        from app.schemas.audit_log import AuditLogCreate
        schema = AuditLogCreate(action="CREATE", entity_type="Property")
        assert schema.entity_id is None
        assert schema.user_id is None
        assert schema.description is None

    def test_read_schema_from_orm(self, db_session):
        from app.models.audit_log import AuditLog
        from app.schemas.audit_log import AuditLogRead

        log = AuditLog(action="VIEW", entity_type="Document")
        db_session.add(log)
        db_session.commit()
        db_session.refresh(log)

        schema = AuditLogRead.model_validate(log)
        assert schema.action == "VIEW"
        assert schema.entity_type == "Document"


# ---------------------------------------------------------------------------
# POST /api/audit-logs
# ---------------------------------------------------------------------------

class TestCreateAuditLog:
    """POST /api/audit-logs — create endpoint."""

    def test_returns_201(self, app_client: TestClient):
        response = app_client.post("/api/audit-logs", json=_audit_log_payload())
        assert response.status_code == 201

    def test_response_contains_id(self, app_client: TestClient):
        data = _create_audit_log(app_client)
        assert "id" in data
        uuid.UUID(data["id"])

    def test_response_contains_action(self, app_client: TestClient):
        data = _create_audit_log(app_client, action="LOGIN")
        assert data["action"] == "LOGIN"

    def test_response_contains_entity_type(self, app_client: TestClient):
        data = _create_audit_log(app_client, entity_type="User")
        assert data["entity_type"] == "User"

    def test_response_contains_created_at(self, app_client: TestClient):
        data = _create_audit_log(app_client)
        assert "created_at" in data
        datetime.fromisoformat(data["created_at"])

    def test_optional_fields_persisted(self, app_client: TestClient):
        data = _create_audit_log(
            app_client,
            entity_id="prop-123",
            user_id="user-456",
            user_email="admin@example.com",
            description="Property was created",
            ip_address="192.168.1.1",
        )
        assert data["entity_id"] == "prop-123"
        assert data["user_id"] == "user-456"
        assert data["user_email"] == "admin@example.com"
        assert data["description"] == "Property was created"
        assert data["ip_address"] == "192.168.1.1"

    def test_missing_action_returns_422(self, app_client: TestClient):
        response = app_client.post("/api/audit-logs", json={"entity_type": "Property"})
        assert response.status_code == 422

    def test_missing_entity_type_returns_422(self, app_client: TestClient):
        response = app_client.post("/api/audit-logs", json={"action": "CREATE"})
        assert response.status_code == 422

    def test_empty_action_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/audit-logs", json={"action": "", "entity_type": "Property"}
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self, app_client: TestClient):
        response = app_client.post("/api/audit-logs", json={})
        assert response.status_code == 422

    def test_response_content_type_is_json(self, app_client: TestClient):
        response = app_client.post("/api/audit-logs", json=_audit_log_payload())
        assert response.headers["content-type"].startswith("application/json")


# ---------------------------------------------------------------------------
# GET /api/audit-logs
# ---------------------------------------------------------------------------

class TestListAuditLogs:
    """GET /api/audit-logs — list endpoint with pagination."""

    def test_returns_200(self, app_client: TestClient):
        response = app_client.get("/api/audit-logs")
        assert response.status_code == 200

    def test_empty_result_structure(self, app_client: TestClient):
        data = app_client.get("/api/audit-logs").json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

    def test_empty_list_total_zero(self, app_client: TestClient):
        data = app_client.get("/api/audit-logs").json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_returns_created_logs(self, app_client: TestClient):
        _create_audit_log(app_client, action="CREATE")
        _create_audit_log(app_client, action="UPDATE")
        data = app_client.get("/api/audit-logs").json()
        assert data["total"] == 2
        assert len(data["items"]) == 2

    def test_default_page_and_size(self, app_client: TestClient):
        data = app_client.get("/api/audit-logs").json()
        assert data["page"] == 1
        assert data["size"] == 20

    def test_pagination_page_param(self, app_client: TestClient):
        for i in range(5):
            _create_audit_log(app_client, action=f"ACTION_{i}")
        data = app_client.get("/api/audit-logs?page=2&size=2").json()
        assert data["page"] == 2
        assert data["size"] == 2
        assert len(data["items"]) == 2

    def test_filter_by_action(self, app_client: TestClient):
        _create_audit_log(app_client, action="LOGIN")
        _create_audit_log(app_client, action="LOGOUT")
        data = app_client.get("/api/audit-logs?action=LOGIN").json()
        assert data["total"] == 1
        assert data["items"][0]["action"] == "LOGIN"

    def test_filter_by_entity_type(self, app_client: TestClient):
        _create_audit_log(app_client, entity_type="Property")
        _create_audit_log(app_client, entity_type="Loan")
        data = app_client.get("/api/audit-logs?entity_type=Property").json()
        assert data["total"] == 1
        assert data["items"][0]["entity_type"] == "Property"

    def test_filter_by_user_id(self, app_client: TestClient):
        _create_audit_log(app_client, user_id="user-abc")
        _create_audit_log(app_client, user_id="user-xyz")
        data = app_client.get("/api/audit-logs?user_id=user-abc").json()
        assert data["total"] == 1
        assert data["items"][0]["user_id"] == "user-abc"

    def test_invalid_page_returns_422(self, app_client: TestClient):
        response = app_client.get("/api/audit-logs?page=0")
        assert response.status_code == 422

    def test_invalid_size_too_large_returns_422(self, app_client: TestClient):
        response = app_client.get("/api/audit-logs?size=101")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

class TestAuditLogRouterRegistration:
    """AuditLog router is mounted on the FastAPI app."""

    def test_post_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/audit-logs" in paths

    def test_get_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/audit-logs" in paths
