"""
Integration tests for the AuditLog endpoints.

These tests require a live PostgreSQL instance and are skipped automatically
when the database is not reachable.  Run them with:

    pytest -m integration tests/integration/test_audit_logs_integration.py

Or with a custom DATABASE_URL:

    DATABASE_URL=postgresql://user:pass@host:5432/db pytest -m integration ...
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError


pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _audit_log_payload(**overrides) -> dict:
    """Return a minimal valid audit log creation payload."""
    base = {
        "action": "CREATE",
        "entity_type": "Property",
        "entity_id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "description": "Integration test entry",
        "ip_address": "127.0.0.1",
    }
    base.update(overrides)
    return base


def _create(pg_client, **overrides) -> dict:
    resp = pg_client.post("/api/audit-logs", json=_audit_log_payload(**overrides))
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Create — correct operation
# ---------------------------------------------------------------------------

class TestAuditLogCreateIntegration:
    """Validates correct operation of the POST /api/audit-logs endpoint."""

    def test_create_audit_log_returns_201(self, pg_client):
        response = pg_client.post("/api/audit-logs", json=_audit_log_payload())
        assert response.status_code == 201

    def test_create_response_has_valid_uuid(self, pg_client):
        body = _create(pg_client)
        assert "id" in body
        uuid.UUID(body["id"])  # raises if invalid

    def test_create_response_preserves_action(self, pg_client):
        body = _create(pg_client, action="LOGIN")
        assert body["action"] == "LOGIN"

    def test_create_response_preserves_entity_type(self, pg_client):
        body = _create(pg_client, entity_type="Loan")
        assert body["entity_type"] == "Loan"

    def test_create_response_preserves_optional_fields(self, pg_client):
        entity_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        body = _create(
            pg_client,
            entity_id=entity_id,
            user_id=user_id,
            user_email="qa@example.com",
            description="Integration test",
            ip_address="10.0.0.1",
        )
        assert body["entity_id"] == entity_id
        assert body["user_id"] == user_id
        assert body["user_email"] == "qa@example.com"
        assert body["description"] == "Integration test"
        assert body["ip_address"] == "10.0.0.1"

    def test_create_response_has_created_at_timestamp(self, pg_client):
        from datetime import datetime
        body = _create(pg_client)
        assert "created_at" in body
        datetime.fromisoformat(body["created_at"])  # must be valid ISO datetime

    def test_create_minimal_payload_succeeds(self, pg_client):
        """Only the required fields (action, entity_type) should be sufficient."""
        response = pg_client.post(
            "/api/audit-logs",
            json={"action": "VIEW", "entity_type": "Document"},
        )
        assert response.status_code == 201

    def test_create_response_content_type_is_json(self, pg_client):
        response = pg_client.post("/api/audit-logs", json=_audit_log_payload())
        assert response.headers["content-type"].startswith("application/json")


# ---------------------------------------------------------------------------
# Create — PostgreSQL persistence confirmation
# ---------------------------------------------------------------------------

class TestAuditLogPersistenceIntegration:
    """Confirms successful interaction with PostgreSQL."""

    def test_create_audit_log_persists_to_postgres(self, pg_client):
        payload = _audit_log_payload(action="LOGIN", entity_type="User")
        created = pg_client.post("/api/audit-logs", json=payload).json()
        fetched = pg_client.get("/api/audit-logs?action=LOGIN").json()
        ids = [item["id"] for item in fetched["items"]]
        assert created["id"] in ids

    def test_record_persisted_with_correct_values(self, pg_client):
        unique_action = f"ACTION_{uuid.uuid4().hex[:6]}"
        created = _create(pg_client, action=unique_action, entity_type="TestEntity")

        results = pg_client.get(f"/api/audit-logs?action={unique_action}").json()
        assert results["total"] >= 1
        item = results["items"][0]
        assert item["id"] == created["id"]
        assert item["action"] == unique_action

    def test_multiple_records_all_persisted(self, pg_client):
        unique_entity = f"BulkTest_{uuid.uuid4().hex[:6]}"
        created_ids = []
        for _ in range(3):
            body = _create(pg_client, entity_type=unique_entity)
            created_ids.append(body["id"])

        results = pg_client.get(f"/api/audit-logs?entity_type={unique_entity}").json()
        result_ids = {item["id"] for item in results["items"]}
        for cid in created_ids:
            assert cid in result_ids

    def test_orm_session_directly_confirms_persistence(self, pg_session):
        """Directly query via SQLAlchemy session to confirm DB row was written."""
        from app.models.audit_log import AuditLog

        unique_action = f"DIRECT_{uuid.uuid4().hex[:8]}"
        log = AuditLog(action=unique_action, entity_type="DirectTest")
        pg_session.add(log)
        pg_session.flush()  # flush without commit to see the row in same session

        fetched = pg_session.query(AuditLog).filter(
            AuditLog.action == unique_action
        ).first()
        assert fetched is not None
        assert fetched.entity_type == "DirectTest"

    def test_rollback_does_not_persist_record(self, pg_session):
        """A rolled-back transaction must not leave rows in the DB."""
        from app.models.audit_log import AuditLog

        unique_action = f"ROLLBACK_{uuid.uuid4().hex[:8]}"
        log = AuditLog(action=unique_action, entity_type="RollbackTest")
        pg_session.add(log)
        pg_session.rollback()

        count = pg_session.query(AuditLog).filter(
            AuditLog.action == unique_action
        ).count()
        assert count == 0


# ---------------------------------------------------------------------------
# Create — error handling
# ---------------------------------------------------------------------------

class TestAuditLogCreateErrorHandlingIntegration:
    """Ensures error handling is correct on the create endpoint."""

    def test_missing_action_returns_422(self, pg_client):
        response = pg_client.post(
            "/api/audit-logs", json={"entity_type": "Property"}
        )
        assert response.status_code == 422

    def test_missing_entity_type_returns_422(self, pg_client):
        response = pg_client.post(
            "/api/audit-logs", json={"action": "CREATE"}
        )
        assert response.status_code == 422

    def test_empty_action_returns_422(self, pg_client):
        response = pg_client.post(
            "/api/audit-logs", json={"action": "", "entity_type": "Property"}
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self, pg_client):
        response = pg_client.post("/api/audit-logs", json={})
        assert response.status_code == 422

    def test_action_exceeding_max_length_returns_422(self, pg_client):
        """action field has a max length of 100 characters."""
        response = pg_client.post(
            "/api/audit-logs",
            json={"action": "A" * 101, "entity_type": "Property"},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# List — correct operation and pagination
# ---------------------------------------------------------------------------

class TestAuditLogListIntegration:
    """Validates correct operation of GET /api/audit-logs."""

    def test_list_audit_logs_returns_200(self, pg_client):
        response = pg_client.get("/api/audit-logs")
        assert response.status_code == 200

    def test_list_audit_logs_pagination_structure(self, pg_client):
        data = pg_client.get("/api/audit-logs").json()
        for key in ("items", "total", "page", "size", "pages"):
            assert key in data, f"Missing key: {key}"

    def test_list_default_page_is_1(self, pg_client):
        data = pg_client.get("/api/audit-logs").json()
        assert data["page"] == 1

    def test_list_default_size_is_20(self, pg_client):
        data = pg_client.get("/api/audit-logs").json()
        assert data["size"] == 20

    def test_list_items_is_list(self, pg_client):
        data = pg_client.get("/api/audit-logs").json()
        assert isinstance(data["items"], list)

    def test_filter_by_entity_type(self, pg_client):
        entity_type = f"TestEntity_{uuid.uuid4().hex[:8]}"
        _create(pg_client, entity_type=entity_type)
        data = pg_client.get(f"/api/audit-logs?entity_type={entity_type}").json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["entity_type"] == entity_type

    def test_filter_by_action(self, pg_client):
        unique_action = f"FILTERACT_{uuid.uuid4().hex[:6]}"
        _create(pg_client, action=unique_action)
        data = pg_client.get(f"/api/audit-logs?action={unique_action}").json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["action"] == unique_action

    def test_filter_by_user_id(self, pg_client):
        unique_user = f"user-{uuid.uuid4().hex}"
        _create(pg_client, user_id=unique_user)
        data = pg_client.get(f"/api/audit-logs?user_id={unique_user}").json()
        assert data["total"] >= 1
        for item in data["items"]:
            assert item["user_id"] == unique_user

    def test_filter_by_unknown_entity_type_returns_empty(self, pg_client):
        data = pg_client.get("/api/audit-logs?entity_type=NonExistentType99999").json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_pagination_size_param(self, pg_client):
        unique_entity = f"PaginationTest_{uuid.uuid4().hex[:6]}"
        for _ in range(5):
            _create(pg_client, entity_type=unique_entity)

        data = pg_client.get(
            f"/api/audit-logs?entity_type={unique_entity}&page=1&size=2"
        ).json()
        assert data["size"] == 2
        assert len(data["items"]) == 2

    def test_pagination_total_reflects_all_records(self, pg_client):
        unique_entity = f"TotalTest_{uuid.uuid4().hex[:6]}"
        for _ in range(4):
            _create(pg_client, entity_type=unique_entity)

        data = pg_client.get(
            f"/api/audit-logs?entity_type={unique_entity}&size=2"
        ).json()
        assert data["total"] >= 4

    def test_invalid_page_zero_returns_422(self, pg_client):
        response = pg_client.get("/api/audit-logs?page=0")
        assert response.status_code == 422

    def test_invalid_size_over_100_returns_422(self, pg_client):
        response = pg_client.get("/api/audit-logs?size=101")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Database condition simulation
# ---------------------------------------------------------------------------

class TestAuditLogDatabaseConditionsIntegration:
    """Tests simulate network and database conditions."""

    def test_db_write_failure_returns_500(self, pg_client):
        """
        Simulate a database write failure (e.g., connection lost after insert).
        The endpoint must return 500 rather than crashing silently.
        """
        from app.main import app
        from app.deps import get_db

        mock_session = MagicMock()
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock(
            side_effect=OperationalError("connection lost", None, None)
        )

        def bad_db():
            yield mock_session

        app.dependency_overrides[get_db] = bad_db
        try:
            response = pg_client.post(
                "/api/audit-logs",
                json={"action": "CREATE", "entity_type": "Property"},
            )
            assert response.status_code == 500
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_db_query_failure_on_list_returns_500(self, pg_client):
        """
        Simulate a database query failure during the list operation.
        """
        from app.main import app
        from app.deps import get_db

        mock_session = MagicMock()
        mock_session.query.side_effect = OperationalError(
            "server closed connection", None, None
        )

        def bad_db():
            yield mock_session

        app.dependency_overrides[get_db] = bad_db
        try:
            response = pg_client.get("/api/audit-logs")
            assert response.status_code == 500
        finally:
            app.dependency_overrides.pop(get_db, None)

    def test_concurrent_creates_produce_distinct_ids(self, pg_client):
        """
        Simulate concurrent uploads by issuing multiple quick POST requests.
        Each must get a distinct UUID.
        """
        unique_entity = f"Concurrent_{uuid.uuid4().hex[:6]}"
        ids = []
        for _ in range(5):
            body = _create(pg_client, entity_type=unique_entity)
            ids.append(body["id"])

        assert len(ids) == len(set(ids)), "Duplicate IDs found in concurrent creates"
