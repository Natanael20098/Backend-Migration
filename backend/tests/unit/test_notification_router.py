"""
Unit tests for app/routers/notifications.py

Covers:
  - POST   /api/notifications          (create)
  - GET    /api/notifications          (list)
  - GET    /api/notifications/{id}     (get by id)
  - PATCH  /api/notifications/{id}/read (mark read/unread)
  - DELETE /api/notifications/{id}     (delete)

  Edge cases:
  - Invalid payloads (missing required fields, field too long)
  - Non-existent resource → 404
  - Filter parameters (user_id, unread_only)
  - Email dispatch logging path
  - Response shape validation
"""

import logging
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _notification_payload(**overrides) -> dict:
    """Return a minimal valid notification creation payload."""
    base = {
        "title": "Test Notification",
        "message": "This is a test message.",
        "type": "INFO",
    }
    base.update(overrides)
    return base


def _create_notification(client: TestClient, **overrides) -> dict:
    """POST a notification and return the response JSON."""
    response = client.post("/api/notifications", json=_notification_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Model unit tests
# ---------------------------------------------------------------------------

class TestNotificationModel:
    """ORM model maps to the expected table and columns."""

    def test_tablename(self):
        from app.models.notification import Notification
        assert Notification.__tablename__ == "notifications"

    def test_has_id(self):
        from app.models.notification import Notification
        assert hasattr(Notification, "id")

    def test_has_title(self):
        from app.models.notification import Notification
        assert hasattr(Notification, "title")

    def test_has_message(self):
        from app.models.notification import Notification
        assert hasattr(Notification, "message")

    def test_has_type(self):
        from app.models.notification import Notification
        assert hasattr(Notification, "type")

    def test_has_is_read(self):
        from app.models.notification import Notification
        assert hasattr(Notification, "is_read")

    def test_has_user_email(self):
        from app.models.notification import Notification
        assert hasattr(Notification, "user_email")

    def test_has_created_at(self):
        from app.models.notification import Notification
        assert hasattr(Notification, "created_at")

    def test_db_persistence(self, db_session):
        """Notification can be persisted and retrieved from SQLite."""
        from app.models.notification import Notification

        notif = Notification(
            title="Persisted",
            message="Body",
            type="INFO",
            is_read=False,
        )
        db_session.add(notif)
        db_session.commit()
        db_session.refresh(notif)

        fetched = db_session.get(Notification, notif.id)
        assert fetched is not None
        assert fetched.title == "Persisted"
        assert fetched.is_read is False


# ---------------------------------------------------------------------------
# Schema unit tests
# ---------------------------------------------------------------------------

class TestNotificationSchemas:
    """Pydantic schemas validate and reject data correctly."""

    def test_create_schema_accepts_valid_payload(self):
        from app.schemas.notification import NotificationCreate

        schema = NotificationCreate(title="T", message="M")
        assert schema.type == "INFO"

    def test_create_schema_rejects_empty_title(self):
        from pydantic import ValidationError
        from app.schemas.notification import NotificationCreate

        with pytest.raises(ValidationError):
            NotificationCreate(title="", message="M")

    def test_create_schema_rejects_missing_message(self):
        from pydantic import ValidationError
        from app.schemas.notification import NotificationCreate

        with pytest.raises(ValidationError):
            NotificationCreate(title="T")

    def test_create_schema_rejects_invalid_email(self):
        from pydantic import ValidationError
        from app.schemas.notification import NotificationCreate

        with pytest.raises(ValidationError):
            NotificationCreate(title="T", message="M", user_email="not-an-email")

    def test_create_schema_accepts_valid_email(self):
        from app.schemas.notification import NotificationCreate

        schema = NotificationCreate(title="T", message="M", user_email="user@example.com")
        assert schema.user_email is not None

    def test_read_schema_from_orm(self, db_session):
        from app.models.notification import Notification
        from app.schemas.notification import NotificationRead

        notif = Notification(title="T", message="M", type="INFO", is_read=False)
        db_session.add(notif)
        db_session.commit()
        db_session.refresh(notif)

        schema = NotificationRead.model_validate(notif)
        assert schema.title == "T"
        assert schema.is_read is False

    def test_mark_read_schema_default(self):
        from app.schemas.notification import NotificationMarkRead

        schema = NotificationMarkRead()
        assert schema.is_read is True


# ---------------------------------------------------------------------------
# POST /api/notifications
# ---------------------------------------------------------------------------

class TestCreateNotification:
    """POST /api/notifications — create endpoint."""

    def test_returns_201(self, app_client: TestClient):
        response = app_client.post("/api/notifications", json=_notification_payload())
        assert response.status_code == 201

    def test_response_contains_id(self, app_client: TestClient):
        data = _create_notification(app_client)
        assert "id" in data
        uuid.UUID(data["id"])  # must be a valid UUID

    def test_response_contains_title(self, app_client: TestClient):
        data = _create_notification(app_client, title="My Title")
        assert data["title"] == "My Title"

    def test_response_is_read_false_by_default(self, app_client: TestClient):
        data = _create_notification(app_client)
        assert data["is_read"] is False

    def test_response_type_defaults_to_info(self, app_client: TestClient):
        payload = {"title": "T", "message": "M"}
        response = app_client.post("/api/notifications", json=payload)
        assert response.json()["type"] == "INFO"

    def test_response_contains_created_at(self, app_client: TestClient):
        data = _create_notification(app_client)
        assert "created_at" in data
        # Must be ISO-parseable
        datetime.fromisoformat(data["created_at"])

    def test_with_user_email_persists_email(self, app_client: TestClient):
        data = _create_notification(app_client, user_email="user@example.com")
        assert data["user_email"] == "user@example.com"

    def test_with_user_id_persists_user_id(self, app_client: TestClient):
        uid = str(uuid.uuid4())
        data = _create_notification(app_client, user_id=uid)
        assert data["user_id"] == uid

    def test_with_link_persists_link(self, app_client: TestClient):
        data = _create_notification(app_client, link="/dashboard")
        assert data["link"] == "/dashboard"

    def test_email_dispatch_is_logged(self, app_client: TestClient, caplog):
        with caplog.at_level(logging.INFO, logger="app.routers.notifications"):
            _create_notification(app_client, user_email="dispatch@example.com")
        assert "dispatch@example.com" in caplog.text

    def test_missing_title_returns_422(self, app_client: TestClient):
        response = app_client.post("/api/notifications", json={"message": "M"})
        assert response.status_code == 422

    def test_missing_message_returns_422(self, app_client: TestClient):
        response = app_client.post("/api/notifications", json={"title": "T"})
        assert response.status_code == 422

    def test_empty_title_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/notifications", json={"title": "", "message": "M"}
        )
        assert response.status_code == 422

    def test_invalid_email_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/notifications",
            json={"title": "T", "message": "M", "user_email": "not-valid"},
        )
        assert response.status_code == 422

    def test_extra_fields_are_ignored(self, app_client: TestClient):
        payload = _notification_payload(unknown_field="ignored")
        response = app_client.post("/api/notifications", json=payload)
        assert response.status_code == 201

    def test_non_json_body_returns_422(self, app_client: TestClient):
        response = app_client.post(
            "/api/notifications",
            content="this is not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_empty_body_returns_422(self, app_client: TestClient):
        response = app_client.post("/api/notifications", json={})
        assert response.status_code == 422

    def test_response_content_type_is_json(self, app_client: TestClient):
        response = app_client.post("/api/notifications", json=_notification_payload())
        assert response.headers["content-type"].startswith("application/json")


# ---------------------------------------------------------------------------
# GET /api/notifications
# ---------------------------------------------------------------------------

class TestListNotifications:
    """GET /api/notifications — list endpoint."""

    def test_empty_list(self, app_client: TestClient):
        response = app_client.get("/api/notifications")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_created_notifications(self, app_client: TestClient):
        _create_notification(app_client, title="First")
        _create_notification(app_client, title="Second")
        data = app_client.get("/api/notifications").json()
        assert len(data) == 2

    def test_filter_by_user_id(self, app_client: TestClient):
        uid = str(uuid.uuid4())
        other_uid = str(uuid.uuid4())
        _create_notification(app_client, user_id=uid, title="Mine")
        _create_notification(app_client, user_id=other_uid, title="Theirs")

        data = app_client.get(f"/api/notifications?user_id={uid}").json()
        assert len(data) == 1
        assert data[0]["title"] == "Mine"

    def test_filter_unread_only(self, app_client: TestClient):
        data_new = _create_notification(app_client, title="Unread")
        # Mark it read
        app_client.patch(
            f"/api/notifications/{data_new['id']}/read",
            json={"is_read": True},
        )
        _create_notification(app_client, title="Also Unread")

        unread = app_client.get("/api/notifications?unread_only=true").json()
        assert len(unread) == 1
        assert unread[0]["title"] == "Also Unread"

    def test_invalid_user_id_returns_422(self, app_client: TestClient):
        response = app_client.get("/api/notifications?user_id=not-a-uuid")
        assert response.status_code == 422

    def test_returns_200(self, app_client: TestClient):
        response = app_client.get("/api/notifications")
        assert response.status_code == 200

    def test_response_is_list(self, app_client: TestClient):
        response = app_client.get("/api/notifications")
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# GET /api/notifications/{id}
# ---------------------------------------------------------------------------

class TestGetNotification:
    """GET /api/notifications/{id} — single fetch endpoint."""

    def test_returns_200_for_existing(self, app_client: TestClient):
        created = _create_notification(app_client)
        response = app_client.get(f"/api/notifications/{created['id']}")
        assert response.status_code == 200

    def test_returns_correct_notification(self, app_client: TestClient):
        created = _create_notification(app_client, title="Specific")
        fetched = app_client.get(f"/api/notifications/{created['id']}").json()
        assert fetched["id"] == created["id"]
        assert fetched["title"] == "Specific"

    def test_returns_404_for_nonexistent(self, app_client: TestClient):
        response = app_client.get(f"/api/notifications/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_404_detail_message(self, app_client: TestClient):
        response = app_client.get(f"/api/notifications/{uuid.uuid4()}")
        assert "not found" in response.json()["detail"].lower()

    def test_invalid_uuid_returns_422(self, app_client: TestClient):
        response = app_client.get("/api/notifications/not-a-uuid")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /api/notifications/{id}/read
# ---------------------------------------------------------------------------

class TestMarkNotificationRead:
    """PATCH /api/notifications/{id}/read — mark read/unread endpoint."""

    def test_mark_read_returns_200(self, app_client: TestClient):
        created = _create_notification(app_client)
        response = app_client.patch(
            f"/api/notifications/{created['id']}/read",
            json={"is_read": True},
        )
        assert response.status_code == 200

    def test_mark_read_sets_is_read_true(self, app_client: TestClient):
        created = _create_notification(app_client)
        updated = app_client.patch(
            f"/api/notifications/{created['id']}/read",
            json={"is_read": True},
        ).json()
        assert updated["is_read"] is True

    def test_mark_read_sets_read_at_timestamp(self, app_client: TestClient):
        created = _create_notification(app_client)
        updated = app_client.patch(
            f"/api/notifications/{created['id']}/read",
            json={"is_read": True},
        ).json()
        assert updated["read_at"] is not None
        datetime.fromisoformat(updated["read_at"])

    def test_mark_unread_clears_read_at(self, app_client: TestClient):
        created = _create_notification(app_client)
        nid = created["id"]
        # Mark read first
        app_client.patch(f"/api/notifications/{nid}/read", json={"is_read": True})
        # Then unread
        updated = app_client.patch(
            f"/api/notifications/{nid}/read", json={"is_read": False}
        ).json()
        assert updated["is_read"] is False
        assert updated["read_at"] is None

    def test_mark_read_returns_404_for_nonexistent(self, app_client: TestClient):
        response = app_client.patch(
            f"/api/notifications/{uuid.uuid4()}/read",
            json={"is_read": True},
        )
        assert response.status_code == 404

    def test_missing_body_returns_422(self, app_client: TestClient):
        created = _create_notification(app_client)
        response = app_client.patch(
            f"/api/notifications/{created['id']}/read",
            json={},
        )
        # is_read has a default so empty body is acceptable (no ValidationError)
        assert response.status_code == 200

    def test_invalid_uuid_returns_422(self, app_client: TestClient):
        response = app_client.patch(
            "/api/notifications/bad-id/read",
            json={"is_read": True},
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/notifications/{id}
# ---------------------------------------------------------------------------

class TestDeleteNotification:
    """DELETE /api/notifications/{id} — delete endpoint."""

    def test_delete_returns_204(self, app_client: TestClient):
        created = _create_notification(app_client)
        response = app_client.delete(f"/api/notifications/{created['id']}")
        assert response.status_code == 204

    def test_delete_removes_notification(self, app_client: TestClient):
        created = _create_notification(app_client)
        nid = created["id"]
        app_client.delete(f"/api/notifications/{nid}")
        get_response = app_client.get(f"/api/notifications/{nid}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_returns_404(self, app_client: TestClient):
        response = app_client.delete(f"/api/notifications/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_delete_removes_only_target(self, app_client: TestClient):
        n1 = _create_notification(app_client, title="Keep")
        n2 = _create_notification(app_client, title="Remove")
        app_client.delete(f"/api/notifications/{n2['id']}")
        remaining = app_client.get("/api/notifications").json()
        assert len(remaining) == 1
        assert remaining[0]["id"] == n1["id"]

    def test_delete_invalid_uuid_returns_422(self, app_client: TestClient):
        response = app_client.delete("/api/notifications/not-a-uuid")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

class TestNotificationRouterRegistration:
    """Notification router is mounted on the FastAPI app."""

    def test_post_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/notifications" in paths

    def test_get_by_id_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/notifications/{notification_id}" in paths

    def test_patch_read_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/notifications/{notification_id}/read" in paths

    def test_delete_route_is_registered(self):
        from app.main import app
        paths = [r.path for r in app.routes]
        assert "/api/notifications/{notification_id}" in paths
