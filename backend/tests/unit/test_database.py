"""
Unit tests for app/core/database.py — engine setup and connectivity helper.

``check_database_connection`` is tested with a mocked engine so no real
PostgreSQL connection is required.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestDatabaseModule:
    """Database module exports the expected objects."""

    def test_engine_is_importable(self):
        from app.core.database import engine
        assert engine is not None

    def test_session_local_is_importable(self):
        from app.core.database import SessionLocal
        assert SessionLocal is not None

    def test_base_is_importable(self):
        from app.core.database import Base
        assert Base is not None

    def test_check_database_connection_is_callable(self):
        from app.core.database import check_database_connection
        assert callable(check_database_connection)


class TestCheckDatabaseConnection:
    """check_database_connection returns True/False without hitting a real DB."""

    def test_returns_true_when_query_succeeds(self):
        from app.core.database import check_database_connection

        mock_conn = MagicMock()
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)

        with patch("app.core.database.engine") as mock_engine:
            mock_engine.connect.return_value = mock_conn
            result = check_database_connection()

        assert result is True

    def test_returns_false_when_connection_fails(self):
        from app.core.database import check_database_connection

        with patch("app.core.database.engine") as mock_engine:
            mock_engine.connect.side_effect = Exception("connection refused")
            result = check_database_connection()

        assert result is False

    def test_returns_false_on_operational_error(self):
        from app.core.database import check_database_connection
        from sqlalchemy.exc import OperationalError

        with patch("app.core.database.engine") as mock_engine:
            mock_engine.connect.side_effect = OperationalError(
                "could not connect", None, None
            )
            result = check_database_connection()

        assert result is False


class TestHealthCheckModel:
    """HealthCheck ORM model maps to the expected table."""

    def test_tablename(self):
        from app.models.health_check import HealthCheck
        assert HealthCheck.__tablename__ == "health_checks"

    def test_has_id_column(self):
        from app.models.health_check import HealthCheck
        assert hasattr(HealthCheck, "id")

    def test_has_status_column(self):
        from app.models.health_check import HealthCheck
        assert hasattr(HealthCheck, "status")

    def test_has_checked_at_column(self):
        from app.models.health_check import HealthCheck
        assert hasattr(HealthCheck, "checked_at")


class TestGetDbDependency:
    """get_db yields a Session and closes it."""

    def test_get_db_yields_session(self):
        from app.deps import get_db
        from sqlalchemy.orm import Session

        gen = get_db()
        session = next(gen)
        assert isinstance(session, Session)
        # Exhaust the generator (triggers finally block)
        try:
            next(gen)
        except StopIteration:
            pass
