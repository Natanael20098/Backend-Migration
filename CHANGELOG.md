# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] – 2025-01-27 14:00

### Added
- **Integration tests** (`backend/tests/integration/test_loan_payment_endpoints.py`):
  - 60 integration tests covering the full LoanPayment REST API against a real PostgreSQL database
  - Tests cover all 8 endpoints: POST, GET list, GET by id, PUT, PATCH, DELETE, GET overdue, GET summary
  - Automatically skip when PostgreSQL is not reachable (CI-safe)
  - Full lifecycle test (create → read → patch → list → delete)
  - Summary aggregation round-trip verification after status changes

- **Unit tests** (`backend/tests/unit/test_loan_payment_logic.py`):
  - 120 unit tests covering all LoanPayment business logic paths
  - Schema validation: `LoanPaymentCreate`, `LoanPaymentUpdate`, `LoanPaymentRead`
  - `VALID_STATUSES` constant completeness tests
  - ORM model column presence and persistence behaviour
  - Overdue detection logic (PENDING + past due_date; boundary conditions)
  - Status transition logic (PENDING → PAID/LATE/MISSED/PARTIAL; invalid rejected)
  - Payment summary aggregation (counts, totals, isolation per loan)
  - Filter logic (by status, loan_application_id, due_date range, combined)
  - Full-replace (PUT) logic; partial-update (PATCH) field isolation

- **Test dependencies** (`backend/pyproject.toml`):
  - Added `pytest`, `pytest-cov`, `httpx` to `[tool.poetry.group.dev.dependencies]`
  - Added `[tool.pytest.ini_options]` with `integration` marker and test path config
  - Added `[tool.coverage.report]` with `fail_under = 80`

### Coverage
- `app/routers/loan_payments.py`: **100%**
- `app/schemas/loan_payment.py`: **100%**
- `app/models/loan_payment.py`: **100%**
- **Total LoanPayment coverage: 100%** (exceeds 80% requirement)
