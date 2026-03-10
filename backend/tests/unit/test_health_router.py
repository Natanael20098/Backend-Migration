"""
Unit tests for app/routers/health.py.

The health router is tested in isolation with:
  - the real SQLite-backed session (via ``app_client`` fixture)
  - mocked ``check_database_connection`` to cover both the 'ok' and 'unavailable'
    branches without a live PostgreSQL connection.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpointStructure:
    """GET /health is wired and returns the correct response shape."""

    def test_health_returns_200(self, app_client: TestClient):
        with patch("app.routers.health.check_database_connection", return_value=True):
            response = app_client.get("/health")
        assert response.status_code == 200

    def test_health_returns_json(self, app_client: TestClient):
        with patch("app.routers.health.check_database_connection", return_value=True):
            response = app_client.get("/health")
        assert response.headers["content-type"].startswith("application/json")

    def test_health_body_has_status_key(self, app_client: TestClient):
        with patch("app.routers.health.check_database_connection", return_value=True):
            response = app_client.get("/health")
        assert "status" in response.json()

    def test_health_body_has_database_key(self, app_client: TestClient):
        with patch("app.routers.health.check_database_connection", return_value=True):
            response = app_client.get("/health")
        assert "database" in response.json()

    def test_health_body_has_last_checked_key(self, app_client: TestClient):
        with patch("app.routers.health.check_database_connection", return_value=True):
            response = app_client.get("/health")
        assert "last_checked" in response.json()


class TestHealthEndpointDBOk:
    """When the database is reachable the endpoint reports db status 'ok'."""

    def test_status_is_ok(self, app_client: TestClient):
        with patch("app.routers.health.check_database_connection", return_value=True):
            response = app_client.get("/health")
        assert response.json()["status"] == "ok"

    def test_database_is_ok(self, app_client: TestClient):
        with patch("app.routers.health.check_database_connection", return_value=True):
            response = app_client.get("/health")
        assert response.json()["database"] == "ok"

    def test_last_checked_is_not_null(self, app_client: TestClient):
        with patch("app.routers.health.check_database_connection", return_value=True):
            response = app_client.get("/health")
        assert response.json()["last_checked"] is not None

    def test_last_checked_is_iso_string(self, app_client: TestClient):
        """last_checked should be parseable as an ISO 8601 datetime string."""
        from datetime import datetime

        with patch("app.routers.health.check_database_connection", return_value=True):
            response = app_client.get("/health")
        ts = response.json()["last_checked"]
        # Will raise ValueError if not ISO-parseable
        datetime.fromisoformat(ts)


class TestHealthEndpointDBUnavailable:
    """When the database is unreachable the endpoint reports db status 'unavailable'."""

    def test_status_still_ok(self, app_client: TestClient):
        with patch("app.routers.health.check_database_connection", return_value=False):
            response = app_client.get("/health")
        assert response.json()["status"] == "ok"

    def test_database_is_unavailable(self, app_client: TestClient):
        with patch("app.routers.health.check_database_connection", return_value=False):
            response = app_client.get("/health")
        assert response.json()["database"] == "unavailable"

    def test_last_checked_is_null_when_db_down(self, app_client: TestClient):
        with patch("app.routers.health.check_database_connection", return_value=False):
            response = app_client.get("/health")
        assert response.json()["last_checked"] is None

    def test_http_status_still_200_when_db_down(self, app_client: TestClient):
        """The HTTP status is 200 regardless — the health endpoint is always up."""
        with patch("app.routers.health.check_database_connection", return_value=False):
            response = app_client.get("/health")
        assert response.status_code == 200
