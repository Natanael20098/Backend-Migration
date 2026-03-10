"""
Alembic environment configuration.

Reads DATABASE_URL from the environment (falling back to the value in
alembic.ini) so migrations work both locally and inside Docker containers.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to the .ini file values
# ---------------------------------------------------------------------------
config = context.config

# Override sqlalchemy.url from environment variable when available
db_url = os.getenv("DATABASE_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import all models so their metadata is available for autogenerate
# ---------------------------------------------------------------------------
from app.core.database import Base  # noqa: E402

import app.models.health_check  # noqa: F401, E402
import app.models.notification  # noqa: F401, E402
import app.models.otp_code  # noqa: F401, E402
import app.models.loan_application  # noqa: F401, E402
import app.models.loan_payment  # noqa: F401, E402

target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Run migrations offline (without a live DB connection)
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — emit SQL to stdout without connecting.
    Useful for generating SQL scripts for DBAs.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Run migrations online (with a live DB connection)
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode — connects to the database and applies
    pending migrations.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
