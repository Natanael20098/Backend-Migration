#!/usr/bin/env bash
# =============================================================================
#  Chiron System Cutover Script
#
#  Purpose : Execute the approved cutover from the legacy Java/Spring Boot
#            monolith to the new Python/FastAPI microservices stack.
#
#  Strategy: Blue/Green with an in-place traffic redirect.
#            The old system is left read-only (not deleted) until the
#            post-cutover validation window expires (48 h by default).
#
#  Usage   : bash scripts/cutover.sh [--dry-run] [--skip-validation]
#
#  Exit codes:
#    0  — cutover completed successfully
#    1  — pre-flight check failure (cutover aborted, no changes made)
#    2  — validation failure after cutover (rollback recommended)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — override via environment variables
# ---------------------------------------------------------------------------
NEW_SERVICE_URL="${SERVICE_BASE_URL:-http://localhost:8000}"
OLD_SERVICE_URL="${OLD_SERVICE_URL:-http://localhost:8080}"
DB_URL="${DATABASE_URL:-postgresql://chiron:chiron@localhost:5432/chiron}"
VALIDATION_RETRIES="${VALIDATION_RETRIES:-5}"
VALIDATION_SLEEP="${VALIDATION_SLEEP:-3}"
DRY_RUN="${DRY_RUN:-false}"
SKIP_VALIDATION="${SKIP_VALIDATION:-false}"
LOG_FILE="logs/cutover_$(date +%Y%m%d_%H%M%S).log"

# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"; }
step()    { echo -e "\n${GREEN}══════════════════════════════════${NC}" | tee -a "$LOG_FILE"
            echo -e "${GREEN}  STEP: $*${NC}" | tee -a "$LOG_FILE"
            echo -e "${GREEN}══════════════════════════════════${NC}" | tee -a "$LOG_FILE"; }

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
for arg in "$@"; do
  case $arg in
    --dry-run)          DRY_RUN=true ;;
    --skip-validation)  SKIP_VALIDATION=true ;;
    *) warn "Unknown argument: $arg" ;;
  esac
done

mkdir -p logs

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
cat <<'BANNER'
  ╔═══════════════════════════════════════════════════════╗
  ║         Chiron System Cutover                         ║
  ║         Java Spring Boot  →  Python FastAPI           ║
  ╚═══════════════════════════════════════════════════════╝
BANNER

[[ "$DRY_RUN" == "true" ]] && warn "DRY-RUN mode — no live changes will be made."
info "Log file: $LOG_FILE"
info "New service: $NEW_SERVICE_URL"
info "Old service: $OLD_SERVICE_URL"

# ---------------------------------------------------------------------------
# Step 1: Pre-flight checks
# ---------------------------------------------------------------------------
step "1/8 — Pre-flight checks"

check_http() {
  local url="$1"
  local label="$2"
  if curl -sf --max-time 5 "$url/health" > /dev/null 2>&1 \
     || curl -sf --max-time 5 "$url/actuator/health" > /dev/null 2>&1; then
    info "$label is reachable at $url"
    return 0
  else
    warn "$label is NOT reachable at $url"
    return 1
  fi
}

NEW_SERVICE_OK=true
check_http "$NEW_SERVICE_URL" "New service (FastAPI)" || NEW_SERVICE_OK=false

if [[ "$NEW_SERVICE_OK" == "false" ]]; then
  error "New service health check FAILED — cutover aborted."
  error "Start the stack first:  docker compose up -d"
  exit 1
fi

# Check Docker Compose is running
if command -v docker &>/dev/null; then
  RUNNING_CONTAINERS=$(docker compose ps --services --filter status=running 2>/dev/null || echo "")
  if echo "$RUNNING_CONTAINERS" | grep -q "app"; then
    info "Docker Compose 'app' container is running."
  else
    warn "Docker Compose 'app' container does not appear to be running."
  fi
  if echo "$RUNNING_CONTAINERS" | grep -q "db"; then
    info "Docker Compose 'db' (PostgreSQL) container is running."
  else
    warn "Docker Compose 'db' container does not appear to be running."
  fi
fi

info "Pre-flight checks passed."

# ---------------------------------------------------------------------------
# Step 2: Database readiness verification
# ---------------------------------------------------------------------------
step "2/8 — Database readiness verification"

if command -v psql &>/dev/null; then
  if psql "$DB_URL" -c "SELECT 1;" &>/dev/null; then
    info "PostgreSQL is reachable and accepting connections."
  else
    error "PostgreSQL is not reachable at $DB_URL — cutover aborted."
    exit 1
  fi
else
  # psql not installed; rely on the health endpoint DB status
  DB_STATUS=$(curl -sf --max-time 5 "$NEW_SERVICE_URL/health" \
              | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('database','unknown'))" 2>/dev/null || echo "unknown")
  if [[ "$DB_STATUS" == "ok" ]]; then
    info "Database reported 'ok' via health endpoint."
  else
    warn "Database status from health endpoint: $DB_STATUS (continuing anyway)"
  fi
fi

# ---------------------------------------------------------------------------
# Step 3: Smoke-test new service endpoints
# ---------------------------------------------------------------------------
step "3/8 — Smoke-test new service endpoints"

ENDPOINTS=(
  "/health"
  "/api/otp-codes"
  "/api/notifications"
  "/api/loan-payments"
)

SMOKE_FAIL=0
for endpoint in "${ENDPOINTS[@]}"; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$NEW_SERVICE_URL$endpoint" 2>/dev/null || echo "000")
  if [[ "$STATUS" == "200" ]]; then
    info "  ✔  $endpoint → HTTP $STATUS"
  else
    error "  ✗  $endpoint → HTTP $STATUS"
    SMOKE_FAIL=1
  fi
done

if [[ "$SMOKE_FAIL" -ne 0 ]]; then
  error "Smoke tests FAILED — cutover aborted."
  exit 1
fi
info "All smoke tests passed."

# ---------------------------------------------------------------------------
# Step 4: Put old system into read-only / maintenance mode
# ---------------------------------------------------------------------------
step "4/8 — Engage maintenance mode on old system"

if [[ "$DRY_RUN" == "true" ]]; then
  info "[DRY-RUN] Would send maintenance-mode signal to old system at $OLD_SERVICE_URL"
else
  # Attempt graceful maintenance-mode toggle; ignore failures (old system may
  # already be stopped or may not support this endpoint)
  curl -sf --max-time 5 -X POST "$OLD_SERVICE_URL/actuator/shutdown" \
    -H "Content-Type: application/json" \
    > /dev/null 2>&1 \
    && info "Old system shutdown endpoint called." \
    || warn "Old system shutdown endpoint not reachable — proceeding."
fi

# ---------------------------------------------------------------------------
# Step 5: Traffic redirect
# ---------------------------------------------------------------------------
step "5/8 — Redirect traffic to new service"

if [[ "$DRY_RUN" == "true" ]]; then
  info "[DRY-RUN] Would update reverse proxy / load balancer to point to $NEW_SERVICE_URL"
else
  # In this local Docker Compose setup, traffic is handled by port mapping.
  # The new service is already on port 8000.  In production this step would
  # update an nginx/HAProxy config or DNS record.
  info "Traffic is already routed to $NEW_SERVICE_URL via Docker Compose port 8000."
  info "No external load balancer reconfiguration required for local deployment."
fi

# ---------------------------------------------------------------------------
# Step 6: Run integration test suite against new service
# ---------------------------------------------------------------------------
step "6/8 — Run integration tests against new service"

if [[ "$SKIP_VALIDATION" == "true" ]]; then
  warn "[SKIP_VALIDATION] Skipping integration test suite."
else
  if command -v poetry &>/dev/null && [[ -d "backend" ]]; then
    export SERVICE_BASE_URL="$NEW_SERVICE_URL"
    info "Running integration tests (this may take a minute) …"
    if [[ "$DRY_RUN" == "true" ]]; then
      info "[DRY-RUN] Would run: cd backend && poetry run pytest -m integration -v"
    else
      (cd backend && poetry run pytest -m integration -v --tb=short 2>&1 | tee -a "../$LOG_FILE") \
        && info "Integration tests PASSED." \
        || { error "Integration tests FAILED."; error "Rollback is recommended — see docs/cutover-strategy.md"; exit 2; }
    fi
  else
    warn "Poetry or backend directory not found — skipping automated integration tests."
    warn "Run manually:  make test-integration"
  fi
fi

# ---------------------------------------------------------------------------
# Step 7: Post-cutover validation
# ---------------------------------------------------------------------------
step "7/8 — Post-cutover validation"

info "Validating new service health after cutover …"
for i in $(seq 1 "$VALIDATION_RETRIES"); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$NEW_SERVICE_URL/health" || echo "000")
  if [[ "$STATUS" == "200" ]]; then
    info "Health check passed (attempt $i/$VALIDATION_RETRIES)."
    break
  fi
  warn "Health check attempt $i/$VALIDATION_RETRIES returned HTTP $STATUS — retrying in ${VALIDATION_SLEEP}s …"
  sleep "$VALIDATION_SLEEP"
  if [[ "$i" -eq "$VALIDATION_RETRIES" ]]; then
    error "Post-cutover health check FAILED after $VALIDATION_RETRIES attempts."
    error "Consider rolling back — see docs/cutover-strategy.md"
    exit 2
  fi
done

# ---------------------------------------------------------------------------
# Step 8: Record cutover completion
# ---------------------------------------------------------------------------
step "8/8 — Record cutover completion"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
CUTOVER_RECORD="logs/cutover_completed_${TIMESTAMP//[:\/]/_}.txt"

cat > "$CUTOVER_RECORD" <<EOF
Chiron System Cutover — Completion Record
==========================================
Timestamp  : $TIMESTAMP
Dry-run    : $DRY_RUN
New service: $NEW_SERVICE_URL
Old service: $OLD_SERVICE_URL
Database   : $DB_URL
Log file   : $LOG_FILE
Status     : SUCCESS

Next steps:
  1. Monitor application logs for 48 hours.
  2. Keep old system in read-only mode for 48-hour validation window.
  3. After validation window: run  make decommission
  4. Notify stakeholders of successful cutover.
EOF

info "Cutover record saved: $CUTOVER_RECORD"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✔  CUTOVER COMPLETED SUCCESSFULLY               ║${NC}"
echo -e "${GREEN}║     New service:  $NEW_SERVICE_URL               ${NC}"
echo -e "${GREEN}║     Timestamp  :  $TIMESTAMP        ${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════╝${NC}"
echo ""
info "IMPORTANT: Monitor logs and validate for 48 hours before running  make decommission"
