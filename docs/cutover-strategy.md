# Chiron System Cutover Strategy and Plan

**Version:** 1.0  
**Date:** 2025-01-27  
**Author:** Engineering Team  
**Status:** Approved  

---

## 1. Executive Summary

This document defines the approved strategy for transitioning the Chiron platform from the legacy Java/Spring Boot monolithic backend to the new Python/FastAPI microservices architecture. It covers the migration approach, step-by-step cutover execution plan, rollback procedures, and post-cutover decommission process.

**New System Stack:**
- Python 3.11 + FastAPI
- PostgreSQL 16 (unchanged)
- Docker Compose for container orchestration
- Poetry 2.x for dependency management

**Old System Stack:**
- Java 17 + Spring Boot
- PostgreSQL (same database, no schema changes)
- Maven build system

---

## 2. Scope

### In Scope
- Backend cutover: Java Spring Boot → Python FastAPI
- Decommissioning of the old Java application process and build artifacts
- Integration test validation against the new service
- Database read/write verification post-cutover

### Out of Scope
- Frontend migration (React/Next.js frontend continues unchanged)
- PostgreSQL schema changes
- External email service configuration changes

---

## 3. Cutover Strategy

### 3.1 Approach: Blue/Green with Read-Only Standby

The selected approach is a **Blue/Green deployment with an in-place traffic redirect**:

| Component  | Blue (Legacy)                    | Green (New)                   |
|-----------|----------------------------------|-------------------------------|
| Runtime   | Java 17 + Spring Boot            | Python 3.11 + FastAPI         |
| Port      | 8080                             | 8000                          |
| Database  | PostgreSQL (shared)              | PostgreSQL (same shared DB)   |
| Build     | Maven (`pom.xml`)                | Poetry (`pyproject.toml`)     |

**Key property:** Both systems share the same PostgreSQL database. Because no schema changes are required, there is zero data migration risk. The new service is started alongside the old one, validated, and then traffic is redirected.

### 3.2 Cutover Timing

| Phase            | Duration     | Notes                                        |
|-----------------|--------------|----------------------------------------------|
| Pre-flight       | 15 minutes   | Health checks, smoke tests                   |
| Traffic redirect | 5 minutes    | Port redirect / proxy config update          |
| Validation       | 30 minutes   | Integration tests + manual spot checks       |
| Monitoring       | 48 hours     | Old system kept in read-only standby         |
| Decommission     | 30 minutes   | After 48-hour validation window expires      |

**Preferred maintenance window:** Tuesday or Wednesday, 02:00–06:00 UTC (low traffic).

---

## 4. Pre-Cutover Checklist

All items must be completed and verified before executing `scripts/cutover.sh`:

- [ ] New Python/FastAPI microservices pass all unit tests: `make test`
- [ ] New service passes all integration tests: `make test-integration`
- [ ] Docker Compose stack starts cleanly: `docker compose up -d`
- [ ] Health endpoint returns `{ "status": "ok", "database": "ok" }` at `/health`
- [ ] All API endpoints respond: `/api/otp-codes`, `/api/notifications`, `/api/loan-payments`
- [ ] PostgreSQL backup taken: `pg_dump $DATABASE_URL > backup_pre_cutover.sql`
- [ ] All active users notified of maintenance window
- [ ] Rollback procedure reviewed and understood by on-call engineer
- [ ] Stakeholder sign-off obtained (see Section 8)
- [ ] `logs/` directory exists and is writable

---

## 5. Step-by-Step Cutover Execution

Execute using the provided script:

```bash
# From project root:
bash scripts/cutover.sh

# Or via Makefile:
make cutover

# Dry-run (no changes, validates checks only):
bash scripts/cutover.sh --dry-run
```

### 5.1 Step 1 — Pre-flight Checks

The script automatically validates:
1. New FastAPI service is reachable at `$SERVICE_BASE_URL` (default: `http://localhost:8000`)
2. Docker Compose `app` and `db` containers are running
3. All required API endpoints return HTTP 200

**Expected output:** All checks pass. If any check fails, the script exits with code 1 and no changes are made.

### 5.2 Step 2 — Database Readiness

1. Verify PostgreSQL connectivity via `pg_isready` or health endpoint
2. Confirm the `database` field in `/health` response equals `"ok"`
3. Confirm all SQLAlchemy models are initialised (tables exist in DB)

### 5.3 Step 3 — Smoke Tests

Automated smoke tests hit all microservice endpoints:

| Endpoint                 | Expected | Notes              |
|--------------------------|----------|--------------------|
| `/health`                | 200      | DB status = ok     |
| `/api/otp-codes`         | 200      | Returns `[]`       |
| `/api/notifications`     | 200      | Returns `[]`       |
| `/api/loan-payments`     | 200      | Returns `[]`       |
| `/api/loan-payments/overdue` | 200  | Returns `[]`       |

### 5.4 Step 4 — Maintenance Mode on Old System

1. Send a graceful shutdown signal to the old Spring Boot application
2. Confirm no new writes are happening to the old system
3. If the old system is already stopped: proceed

**Note:** In the local Docker Compose setup, the old Java system runs on port 8080 (if present). It is stopped via `POST /actuator/shutdown` or `kill -TERM`.

### 5.5 Step 5 — Traffic Redirect

In the local Docker Compose environment:
- New service is already exposed on port 8000
- No load balancer or reverse proxy reconfiguration is required
- Frontend is configured to point to `http://localhost:8000` via `NEXT_PUBLIC_API_URL`

For production deployments: update nginx/HAProxy/DNS to route all traffic to port 8000.

### 5.6 Step 6 — Integration Test Validation

Full integration test suite runs against the live service:

```bash
cd backend && SERVICE_BASE_URL=http://localhost:8000 poetry run pytest -m integration -v
```

All tests in `tests/integration/` must pass. Test failures trigger exit code 2 and block continuation.

### 5.7 Step 7 — Post-Cutover Health Monitoring

1. Poll `/health` every 3 seconds for 5 attempts
2. All attempts must return HTTP 200 with `{ "database": "ok" }`
3. Monitor application logs: `docker compose logs -f app`

### 5.8 Step 8 — Completion Record

The script writes a timestamped completion record to `logs/cutover_completed_*.txt`. This file is required by the decommission script as proof of successful cutover.

---

## 6. Rollback Scenarios

### 6.1 Rollback Trigger Conditions

Initiate rollback if **any** of the following occur during or after cutover:

| Condition                               | Severity | Action           |
|----------------------------------------|----------|------------------|
| New service health check fails         | Critical | Immediate rollback |
| Integration tests fail (> 10% failure) | Critical | Immediate rollback |
| Database connectivity lost             | Critical | Immediate rollback |
| API response time > 5x baseline        | High     | Investigate; rollback if not resolved in 30 min |
| Individual endpoint returns 500        | Medium   | Investigate; patch or rollback |
| Non-critical test failure (< 5%)       | Low      | Log and monitor; rollback optional |

### 6.2 Rollback Procedure

#### Step R1 — Restart the Old Java System

```bash
# If the JAR is available locally:
java -jar target/chiron-*.jar &

# Or if using Docker:
docker run -p 8080:8080 chiron-java:latest
```

#### Step R2 — Redirect Traffic Back to Port 8080

Update the frontend's API URL to point to `http://localhost:8080`.  
In nginx/HAProxy: revert the upstream to port 8080.

#### Step R3 — Verify Old System is Healthy

```bash
curl http://localhost:8080/actuator/health
# Expected: { "status": "UP" }
```

#### Step R4 — Diagnose the New System Failure

1. Check logs: `docker compose logs app`
2. Check database: `psql $DATABASE_URL -c "SELECT COUNT(*) FROM health_checks;"`
3. Re-run the test suite in verbose mode: `make test-all`
4. Fix the identified issue, run tests again, reschedule cutover

#### Step R5 — Document and Notify

Record the failure reason, affected endpoints, and resolution steps.  
Notify all stakeholders within 1 hour of rollback initiation.

### 6.3 Rollback Decision Matrix

```
Cutover started
    │
    ├─ Pre-flight fails ──────────────────────► ABORT (no changes made)
    │
    ├─ Smoke tests fail ─────────────────────► ABORT (no changes made)
    │
    ├─ Old system stopped
    │   ├─ Integration tests fail ──────────► ROLLBACK (restart old system)
    │   └─ Integration tests pass
    │       ├─ Post-cutover health fails ───► ROLLBACK (restart old system)
    │       └─ Post-cutover health passes
    │           └─ Monitoring window (48h)
    │               ├─ Critical issue ──────► ROLLBACK
    │               └─ No issues ──────────► DECOMMISSION
```

---

## 7. Post-Cutover Validation (48-Hour Window)

During the 48-hour monitoring window after cutover, the following checks must pass:

### Hourly Checks (first 4 hours)
- [ ] `GET /health` returns `{ "status": "ok", "database": "ok" }`
- [ ] No 5xx errors in application logs: `docker compose logs app | grep -c "ERROR"`
- [ ] Response times within acceptable range (P95 < 500ms)

### Daily Checks
- [ ] Database record counts stable (no unexpected growth/loss)
- [ ] All microservice endpoints responding correctly
- [ ] No memory leaks: `docker stats` shows stable memory usage

### Sign-off Criteria
All hourly and daily checks must pass before proceeding to decommission. If any check fails, evaluate whether to rollback or patch.

---

## 8. Decommission Procedure

After the 48-hour validation window has passed without issues:

```bash
# From project root:
bash scripts/decommission.sh

# Or via Makefile:
make decommission

# Dry-run first (recommended):
bash scripts/decommission.sh --dry-run
```

The decommission script:
1. Verifies the new service is still healthy
2. Confirms the cutover completion record exists
3. Creates a final database backup
4. Stops any remaining Java processes
5. Archives Java JAR files and source code to `backups/`
6. Archives `pom.xml` for compliance/audit purposes
7. Records the decommission event with timestamp

**Archive retention:** Archived Java artifacts are retained for 90 days before permanent deletion (per standard retention policy).

---

## 9. Stakeholder Approval

This cutover plan has been reviewed and approved by:

| Role               | Name        | Date       | Signature    |
|-------------------|-------------|------------|--------------|
| Engineering Lead   | ___________ | __________ | ____________ |
| Product Owner      | ___________ | __________ | ____________ |
| Operations         | ___________ | __________ | ____________ |
| QA Lead            | ___________ | __________ | ____________ |

**Instructions:**
- All four signatures are required before executing `scripts/cutover.sh` in production.
- For local/development environments, Engineering Lead sign-off is sufficient.
- The signed document should be stored in the project wiki or shared drive.

---

## 10. Communication Plan

| Event                         | Who to Notify           | Method         | Timing            |
|------------------------------|------------------------|----------------|-------------------|
| Maintenance window announcement | All users            | Email          | 48 hours before   |
| Cutover start                 | Engineering team        | Slack / chat   | At start          |
| Cutover complete              | All stakeholders        | Email          | Within 1 hour     |
| Rollback (if triggered)       | All stakeholders        | Email + call   | Immediately       |
| Decommission complete         | Engineering team        | Slack / chat   | At completion     |

---

## 11. Risk Register

| Risk                                  | Probability | Impact   | Mitigation                                     |
|--------------------------------------|-------------|----------|------------------------------------------------|
| New service has undiscovered bugs     | Low         | High     | Integration + unit test suite; staged rollout  |
| Database connectivity issues          | Very Low    | Critical | Same DB instance; no schema changes; rollback ready |
| Shared DB write conflicts             | Very Low    | Medium   | Both services write to separate tables; no overlap |
| Docker resource exhaustion            | Low         | Medium   | Monitor `docker stats`; set container limits   |
| Old system shutdown fails             | Low         | Low      | Force-kill fallback; old system in read-only   |
| Frontend API URL misconfiguration     | Low         | High     | Verify `NEXT_PUBLIC_API_URL` before cutover    |

---

## 12. Quick Reference

```bash
# Start Docker Compose stack
docker compose up -d

# Run unit tests only (no DB required)
make test

# Run integration tests (Docker stack must be running)
make test-integration

# Execute cutover
make cutover

# Decommission old system (after 48-hour window)
make decommission

# View logs
docker compose logs -f app

# Rollback: restart old system on port 8080
java -jar target/chiron-*.jar --server.port=8080
```

---

*Document version 1.0 — maintained by the Chiron Engineering Team.*
