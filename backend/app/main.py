from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.database import Base, engine, check_database_connection
from app.routers import health
from app.routers import notifications
from app.routers import otp_codes
from app.routers import loan_payments

# Import models so SQLAlchemy registers them with Base metadata before create_all
import app.models.health_check  # noqa: F401
import app.models.notification  # noqa: F401
import app.models.otp_code  # noqa: F401
import app.models.loan_application  # noqa: F401
import app.models.loan_payment  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables that belong to this service if DB is reachable
    if check_database_connection():
        Base.metadata.create_all(bind=engine)
    yield
    # Shutdown: dispose the connection pool cleanly
    engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(notifications.router)
app.include_router(otp_codes.router)
app.include_router(loan_payments.router)


@app.get("/")
def root() -> dict:
    """Root endpoint — confirms the application is running."""
    return {"message": f"Welcome to {settings.app_name} v{settings.app_version}"}
