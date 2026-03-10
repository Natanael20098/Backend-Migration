"""
Unit tests for app/main.py — FastAPI application bootstrap.

These tests use an in-memory SQLite database (via the ``app_client`` fixture)
and mock the database-connectivity check so they never require a running
PostgreSQL instance.
"""

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Application instantiation
# ---------------------------------------------------------------------------

class TestAppBootstrap:
    """FastAPI application boots correctly and exposes expected metadata."""

    def test_app_instance_is_fastapi(self):
        from app.main import app
        from fastapi import FastAPI

        assert isinstance(app, FastAPI)

    def test_app_title_from_settings(self):
        from app.main import app
        from app.core.config import settings

        assert app.title == settings.app_name

    def test_app_version_from_settings(self):
        from app.main import app
        from app.core.config import settings

        assert app.version == settings.app_version

    def test_debug_flag_from_settings(self):
        from app.main import app
        from app.core.config import settings

        assert app.debug == settings.debug


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

class TestRootEndpoint:
    """GET / returns a 200 with the expected welcome message."""

    def test_root_returns_200(self, app_client: TestClient):
        response = app_client.get("/")
        assert response.status_code == 200

    def test_root_returns_json(self, app_client: TestClient):
        response = app_client.get("/")
        assert response.headers["content-type"].startswith("application/json")

    def test_root_message_contains_app_name(self, app_client: TestClient):
        from app.core.config import settings

        response = app_client.get("/")
        body = response.json()
        assert "message" in body
        assert settings.app_name in body["message"]

    def test_root_message_contains_version(self, app_client: TestClient):
        from app.core.config import settings

        response = app_client.get("/")
        body = response.json()
        assert settings.app_version in body["message"]

    def test_unknown_path_returns_404(self, app_client: TestClient):
        response = app_client.get("/does-not-exist")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Router registration
# ---------------------------------------------------------------------------

class TestRouterRegistration:
    """The health router is mounted and reachable."""

    def test_health_route_is_registered(self):
        from app.main import app

        routes = [r.path for r in app.routes]
        assert "/health" in routes

    def test_root_route_is_registered(self):
        from app.main import app

        routes = [r.path for r in app.routes]
        assert "/" in routes
