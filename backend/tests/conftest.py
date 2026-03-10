"""
Shared pytest fixtures for both unit and integration test suites.

Unit tests use an in-memory SQLite database so they never require a running
PostgreSQL instance.  Integration tests are marked with the ``integration``
marker and are only collected when the environment variable
``INTEGRATION_TESTS=1`` is set (or when Docker Compose is up).
"""

import os
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# In-memory SQLite engine used by unit tests
# ---------------------------------------------------------------------------
SQLITE_URL = "sqlite://"  # pure in-memory, no file

sqlite_engine = create_engine(
    SQLITE_URL,
    connect_args={"check_same_thread": False},
)
SqliteSession = sessionmaker(bind=sqlite_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session")
def unit_engine():
    """Create all tables in the in-memory SQLite DB once per test session."""
    # Import models to ensure they are registered with Base before create_all
    import app.models.health_check  # noqa: F401
    import app.models.notification  # noqa: F401
    import app.models.otp_code  # noqa: F401
    import app.models.loan_application  # noqa: F401
    import app.models.loan_payment  # noqa: F401
    from app.core.database import Base

    Base.metadata.create_all(bind=sqlite_engine)
    yield sqlite_engine
    sqlite_engine.dispose()


@pytest.fixture()
def db_session(unit_engine):
    """
    Yield a SQLAlchemy session backed by SQLite.
    Each test gets a clean transaction that is rolled back afterwards so tests
    are fully isolated.
    """
    connection = unit_engine.connect()
    transaction = connection.begin()
    session = SqliteSession(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def app_client(db_session):
    """
    Return a FastAPI TestClient whose database dependency is overridden to use
    the in-memory SQLite session so no real PostgreSQL is needed.
    """
    from app.main import app
    from app.deps import get_db

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# PostgreSQL integration fixtures
# ---------------------------------------------------------------------------

PG_URL = os.getenv(
    "DATABASE_URL", "postgresql://chiron:chiron@localhost:5432/chiron"
)

# Name used to mark integration tests so they can be skipped when no DB is up
integration_mark = pytest.mark.integration


@pytest.fixture(scope="session")
def pg_engine():
    """
    Create a SQLAlchemy engine connected to the real PostgreSQL instance.
    Skips all integration tests gracefully when the DB is not reachable.
    """
    from sqlalchemy import create_engine as sa_create_engine
    import app.models.health_check  # noqa: F401
    import app.models.notification  # noqa: F401
    import app.models.otp_code  # noqa: F401
    import app.models.loan_application  # noqa: F401
    import app.models.loan_payment  # noqa: F401
    from app.core.database import Base

    engine = sa_create_engine(PG_URL, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL not reachable at {PG_URL}: {exc}")

    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def pg_session(pg_engine):
    """
    Yield a session against the real PostgreSQL DB.
    Each test runs inside a savepoint so no committed rows escape.
    """
    PgSession = sessionmaker(bind=pg_engine, autocommit=False, autoflush=False)
    connection = pg_engine.connect()
    transaction = connection.begin()
    session = PgSession(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def pg_client(pg_session):
    """
    Return a FastAPI TestClient wired to the real PostgreSQL session.
    Used exclusively by integration tests.
    """
    from app.main import app
    from app.deps import get_db

    def override_get_db():
        yield pg_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
    app.dependency_overrides.clear()
