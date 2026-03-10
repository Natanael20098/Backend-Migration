# =============================================================================
#  Chiron Backend — Developer Makefile
#  Usage:  make <target>
# =============================================================================

.PHONY: help up down build logs \
        test test-unit test-integration test-all test-cov \
        cutover decommission

BACKEND_DIR := backend
COMPOSE     := docker compose
PYTEST      := cd $(BACKEND_DIR) && poetry run pytest

# Default target
help:
	@echo ""
	@echo "  Chiron Backend — available make targets"
	@echo ""
	@echo "  Docker Compose"
	@echo "  ─────────────────────────────────────────"
	@echo "  up                 Start all services (db + app)"
	@echo "  down               Stop and remove containers"
	@echo "  build              Re-build the app Docker image"
	@echo "  logs               Tail container logs"
	@echo ""
	@echo "  Testing"
	@echo "  ─────────────────────────────────────────"
	@echo "  test               Run unit tests only (no DB required)"
	@echo "  test-unit          Same as 'test'"
	@echo "  test-integration   Run integration tests (requires Docker stack)"
	@echo "  test-all           Run unit + integration tests"
	@echo "  test-cov           Run unit tests with coverage report"
	@echo ""
	@echo "  Operations"
	@echo "  ─────────────────────────────────────────"
	@echo "  cutover            Execute the system cutover script"
	@echo "  decommission       Run the old-system decommission script"
	@echo ""

# ---------------------------------------------------------------------------
#  Docker Compose
# ---------------------------------------------------------------------------

up:
	$(COMPOSE) up -d
	@echo "Services started. App: http://localhost:8000  DB: localhost:5432"

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs -f

# ---------------------------------------------------------------------------
#  Testing
#  Unit tests use in-memory SQLite — no running DB needed.
#  Integration tests use httpx against the Docker Compose stack.
# ---------------------------------------------------------------------------

test:
	$(PYTEST) -m "not integration" -v

test-unit:
	$(PYTEST) -m "not integration" -v

test-integration:
	@echo "Running integration tests against $(or $(SERVICE_BASE_URL),http://localhost:8000) ..."
	@echo "Ensure Docker Compose is running:  make up"
	$(PYTEST) -m integration -v

test-all:
	$(PYTEST) -v

test-cov:
	$(PYTEST) -m "not integration" --cov=app --cov-report=term-missing --cov-report=html:htmlcov -v

# ---------------------------------------------------------------------------
#  Operations
# ---------------------------------------------------------------------------

cutover:
	@bash scripts/cutover.sh

decommission:
	@bash scripts/decommission.sh
