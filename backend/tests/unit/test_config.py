"""
Unit tests for app/core/config.py — Settings loading and defaults.
"""

import pytest


class TestSettings:
    """Settings are loaded with expected defaults."""

    def test_settings_is_importable(self):
        from app.core.config import settings
        assert settings is not None

    def test_default_app_name(self):
        from app.core.config import settings
        assert settings.app_name == "Chiron Backend"

    def test_default_app_version(self):
        from app.core.config import settings
        assert settings.app_version == "0.1.0"

    def test_database_url_is_set(self):
        from app.core.config import settings
        assert settings.database_url
        assert settings.database_url.startswith("postgresql://")

    def test_database_url_contains_host(self):
        from app.core.config import settings
        # Must have a host segment — either 'db' (Docker) or 'localhost' (local)
        assert "db" in settings.database_url or "localhost" in settings.database_url

    def test_debug_is_bool(self):
        from app.core.config import settings
        assert isinstance(settings.debug, bool)

    def test_settings_env_override(self, monkeypatch):
        """Environment variables override default values."""
        monkeypatch.setenv("APP_NAME", "Test Override")
        monkeypatch.setenv("APP_VERSION", "9.9.9")
        # Re-instantiate Settings to pick up the patched env
        from app.core.config import Settings
        overridden = Settings()
        assert overridden.app_name == "Test Override"
        assert overridden.app_version == "9.9.9"
