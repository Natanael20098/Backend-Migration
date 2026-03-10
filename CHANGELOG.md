# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] – 2026-03-10 01:00

### Added (System Hardening — Test Phase)

- **In-Process Integration Tests** (`backend/tests/integration/test_all_endpoints_in_process.py`):
  - 107 tests covering ALL endpoints using FastAPI TestClient backed by SQLite (no Docker needed)
  - `TestRootEndpoint` — 3 tests: root 200, message field, content-type
  - `TestHealthEndpoint` — 6 tests: 200, all response fields, content-type, method enforcement
  - `TestOtpCodesEndpoints` — 31 tests: send-otp, verify-otp, list/get/delete, rate-limiting, no code leak
  - `TestNotificationEndpoints` — 30 tests: full CRUD, mark-read/unread, filter, validation
  - `TestLoanPaymentEndpoints` — 31 tests: full CRUD, overdue, summary, lifecycle
  - `TestCrossServiceInteractions` — 6 tests: OpenAPI schema, docs endpoints, cross-service isolation
  - All tests fully independent and CI/CD safe (no external dependencies)

- **Security Audit Tests** (`backend/tests/security/test_auth_security_audit.py`):
  - 66 tests aligned with OWASP Top 10 categories
  - `TestA01BrokenAccessControl` — 10 tests: HTTP method enforcement, path traversal resistance
  - `TestA02CryptographicFailures` — 8 tests: OTP code never leaks, token structure, no DB details
  - `TestA03Injection` — 12 tests: SQL injection, XSS, null bytes, type coercion, oversized inputs
  - `TestA04InsecureDesign` — 12 tests: single-use OTP, expiry, case-insensitive email lookup
  - `TestA05SecurityMisconfiguration` — 8 tests: no stack traces, no DB info in errors
  - `TestA07IdentificationAndAuthentication` — 10 tests: 401 on bad creds, rate limiting, ambiguous messages
  - `TestA09SecurityLoggingAndMonitoring` — 6 tests: failed auth, success, rate-limit and CRUD ops logged

- **Report Generation** (`backend/scripts/run_tests_with_reports.sh`, `backend/reports/`):
  - Shell script generating HTML + JUnit XML reports for both integration and security test suites
  - `reports/integration-report.html` + `reports/integration-report.xml`
  - `reports/security-audit.html` + `reports/security-audit.xml`
  - `pytest-html` added to dev dependencies

- **pyproject.toml** — registered `security` pytest marker (eliminates warnings), added `pytest-html` dependency

## [Unreleased] – 2025-01-27 15:30

### Added (System Hardening and Cutover)

- **Integration Testing Framework** (`backend/tests/integration/test_all_microservices.py`):
  - 41 httpx-based integration tests covering all three microservices against the Dockerized local environment
  - `TestHealthEndpoint` — 4 tests: health check returns 200, status/database fields, content-type
  - `TestRootEndpoint` — 2 tests: root endpoint reachable, response has message
  - `TestOtpCodesService` — 6 tests: list, create, validation (missing email/code returns 422)
  - `TestNotificationsService` — 7 tests: list, create, get-by-id, 404 on unknown id, validation
  - `TestLoanPaymentsService` — 18 tests: full CRUD lifecycle, overdue detection, summary, 422 validations
  - `TestCrossServiceInteractions` — 3 tests: shared DB health, service independence, all endpoints respond
  - Automatically skipped when Docker stack is not running (CI-safe via `httpx.ConnectError` handler)

- **Makefile** (`Makefile`):
  - `make test` / `make test-unit` — run unit tests only (no DB required)
  - `make test-integration` — run integration tests against Docker Compose stack
  - `make test-all` — run all tests
  - `make test-cov` — unit tests with HTML coverage report
  - `make up` / `make down` / `make build` / `make logs` — Docker Compose management
  - `make cutover` / `make decommission` — operations

- **Cutover Script** (`scripts/cutover.sh`):
  - 8-step automated cutover from Java/Spring Boot to Python/FastAPI
  - Pre-flight checks: new service health, Docker containers running, smoke tests on all endpoints
  - Database readiness verification
  - Maintenance mode engagement on old system
  - Traffic redirect to new service
  - Full integration test suite execution against live service
  - Post-cutover health polling with configurable retry logic
  - Timestamped completion record written to `logs/`
  - `--dry-run` mode: validates all checks without making live changes
  - Exit codes: 0 = success, 1 = pre-flight failure (no changes), 2 = post-cutover validation failure

- **Decommission Script** (`scripts/decommission.sh`):
  - 5-step safe decommission of the legacy Java system
  - Safety gate: refuses to run if new service is unhealthy
  - Requires cutover completion record (produced by `cutover.sh`)
  - Pre-decommission PostgreSQL database backup via `pg_dump`
  - Graceful stop of Java processes; force-kill fallback
  - Archives Java JARs, source (`src/main/java`), and `pom.xml` to `backups/`
  - `--dry-run` and `--force` flags
  - Timestamped decommission record written to `logs/`

- **Cutover Strategy Document** (`docs/cutover-strategy.md`):
  - Comprehensive Blue/Green cutover plan with in-place traffic redirect
  - Detailed pre-cutover checklist (12 items)
  - Step-by-step execution guide (8 steps matching the cutover script)
  - Rollback decision matrix with 6 trigger conditions and severity levels
  - Step-by-step rollback procedure (5 steps)
  - 48-hour post-cutover validation window with hourly/daily checks
  - Decommission procedure reference
  - Stakeholder approval table
  - Communication plan
  - Risk register (6 identified risks with mitigations)
  - Quick-reference command cheat-sheet

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
