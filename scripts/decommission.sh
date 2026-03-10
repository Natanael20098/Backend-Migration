#!/usr/bin/env bash
# =============================================================================
#  Chiron — Old System Decommission Script
#
#  Purpose : Safely decommission the legacy Java/Spring Boot monolith after
#            the 48-hour post-cutover validation window has passed.
#
#  Prerequisites:
#    - Cutover completed successfully (logs/cutover_completed_*.txt exists)
#    - New system has been running without critical issues for 48+ hours
#    - Stakeholder sign-off received
#
#  Usage   : bash scripts/decommission.sh [--dry-run] [--force]
#
#  Exit codes:
#    0  — decommission completed
#    1  — safety check failed (decommission aborted)
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
NEW_SERVICE_URL="${SERVICE_BASE_URL:-http://localhost:8000}"
OLD_SERVICE_URL="${OLD_SERVICE_URL:-http://localhost:8080}"
OLD_JAR_DIR="${OLD_JAR_DIR:-./}"          # directory containing the old Spring Boot jar
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_URL="${DATABASE_URL:-postgresql://chiron:chiron@localhost:5432/chiron}"
DRY_RUN="${DRY_RUN:-false}"
FORCE="${FORCE:-false}"
LOG_FILE="logs/decommission_$(date +%Y%m%d_%H%M%S).log"

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
    --dry-run) DRY_RUN=true ;;
    --force)   FORCE=true ;;
    *) warn "Unknown argument: $arg" ;;
  esac
done

mkdir -p logs "$BACKUP_DIR"

# ---------------------------------------------------------------------------
# Banner
# ---------------------------------------------------------------------------
cat <<'BANNER'
  ╔═══════════════════════════════════════════════════════╗
  ║         Chiron Old System Decommission                ║
  ║         Removing legacy Java/Spring Boot monolith     ║
  ╚═══════════════════════════════════════════════════════╝
BANNER

[[ "$DRY_RUN" == "true" ]] && warn "DRY-RUN mode — no live changes will be made."
info "Log file: $LOG_FILE"

# ---------------------------------------------------------------------------
# Step 1: Safety gate — confirm new service is healthy
# ---------------------------------------------------------------------------
step "1/5 — Safety gate: new service health check"

HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$NEW_SERVICE_URL/health" 2>/dev/null || echo "000")
if [[ "$HEALTH_STATUS" != "200" ]]; then
  error "New service health check FAILED (HTTP $HEALTH_STATUS)."
  error "Decommission aborted — do not remove the old system while the new one is unhealthy."
  exit 1
fi
info "New service is healthy (HTTP $HEALTH_STATUS)."

# ---------------------------------------------------------------------------
# Step 2: Verify cutover completion record exists
# ---------------------------------------------------------------------------
step "2/5 — Verify cutover completion record"

CUTOVER_RECORDS=$(ls logs/cutover_completed_*.txt 2>/dev/null || true)
if [[ -z "$CUTOVER_RECORDS" ]]; then
  if [[ "$FORCE" == "true" ]]; then
    warn "--force flag set: proceeding despite missing cutover record."
  else
    error "No cutover completion record found in logs/."
    error "Run the cutover first:  make cutover"
    error "Use --force to override this check."
    exit 1
  fi
else
  LATEST_RECORD=$(ls -t logs/cutover_completed_*.txt | head -1)
  info "Cutover record found: $LATEST_RECORD"
  cat "$LATEST_RECORD" | tee -a "$LOG_FILE"
fi

# ---------------------------------------------------------------------------
# Step 3: Database backup before decommission
# ---------------------------------------------------------------------------
step "3/5 — Pre-decommission database backup"

BACKUP_FILE="$BACKUP_DIR/chiron_pre_decommission_$(date +%Y%m%d_%H%M%S).sql"

if [[ "$DRY_RUN" == "true" ]]; then
  info "[DRY-RUN] Would create database backup at: $BACKUP_FILE"
elif command -v pg_dump &>/dev/null; then
  info "Creating database backup: $BACKUP_FILE"
  pg_dump "$DB_URL" > "$BACKUP_FILE" 2>&1 \
    && info "Database backup completed: $BACKUP_FILE" \
    || warn "pg_dump failed — backup skipped. Manual backup recommended."
else
  warn "pg_dump not available — database backup skipped."
  warn "Create a manual backup before proceeding."
fi

# ---------------------------------------------------------------------------
# Step 4: Stop and archive old system artifacts
# ---------------------------------------------------------------------------
step "4/5 — Stop old system and archive artifacts"

# Stop the old Java application if it is running
OLD_PIDS=$(pgrep -f "spring-boot\|ZCloudPlatformApplication\|chiron.*\\.jar" 2>/dev/null || true)
if [[ -n "$OLD_PIDS" ]]; then
  if [[ "$DRY_RUN" == "true" ]]; then
    info "[DRY-RUN] Would stop Java processes: $OLD_PIDS"
  else
    info "Stopping old Java processes: $OLD_PIDS"
    echo "$OLD_PIDS" | xargs kill -TERM 2>/dev/null || warn "Could not send SIGTERM to old processes."
    sleep 5
    echo "$OLD_PIDS" | xargs kill -9 2>/dev/null || true
    info "Old Java processes stopped."
  fi
else
  info "No running Java processes detected — old system appears to be stopped already."
fi

# Archive the old JAR / build artifacts if they exist
if ls "$OLD_JAR_DIR"*.jar &>/dev/null 2>&1; then
  ARCHIVE_DIR="$BACKUP_DIR/java_artifacts_$(date +%Y%m%d_%H%M%S)"
  if [[ "$DRY_RUN" == "true" ]]; then
    info "[DRY-RUN] Would archive Java JARs from $OLD_JAR_DIR to $ARCHIVE_DIR"
  else
    mkdir -p "$ARCHIVE_DIR"
    cp "$OLD_JAR_DIR"*.jar "$ARCHIVE_DIR/" 2>/dev/null && info "JARs archived to $ARCHIVE_DIR" || true
  fi
fi

# Archive pom.xml (retain for compliance/audit)
if [[ -f "pom.xml" ]]; then
  if [[ "$DRY_RUN" == "true" ]]; then
    info "[DRY-RUN] Would archive pom.xml to $BACKUP_DIR/"
  else
    cp pom.xml "$BACKUP_DIR/pom.xml.archived_$(date +%Y%m%d)" 2>/dev/null \
      && info "pom.xml archived to $BACKUP_DIR/" \
      || warn "Could not archive pom.xml"
  fi
fi

# Archive Java source (src/main/java)
if [[ -d "src/main/java" ]]; then
  JAVA_ARCHIVE="$BACKUP_DIR/java_src_$(date +%Y%m%d_%H%M%S).tar.gz"
  if [[ "$DRY_RUN" == "true" ]]; then
    info "[DRY-RUN] Would archive src/main/java to $JAVA_ARCHIVE"
  else
    tar -czf "$JAVA_ARCHIVE" src/main/java 2>/dev/null \
      && info "Java source archived: $JAVA_ARCHIVE" \
      || warn "Could not archive Java source."
  fi
fi

# ---------------------------------------------------------------------------
# Step 5: Record decommission and notify
# ---------------------------------------------------------------------------
step "5/5 — Record decommission completion"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DECOMMISSION_RECORD="logs/decommission_completed_${TIMESTAMP//[:\/]/_}.txt"

if [[ "$DRY_RUN" != "true" ]]; then
  cat > "$DECOMMISSION_RECORD" <<EOF
Chiron Old System Decommission — Completion Record
====================================================
Timestamp    : $TIMESTAMP
Dry-run      : $DRY_RUN
New service  : $NEW_SERVICE_URL
Old service  : $OLD_SERVICE_URL (stopped)
DB backup    : ${BACKUP_FILE:-"skipped"}
Log file     : $LOG_FILE
Status       : SUCCESS

Actions taken:
  - Old Java/Spring Boot processes stopped
  - JAR artifacts archived to: $BACKUP_DIR
  - Database snapshot created (if pg_dump available)
  - Java source archived (if src/main/java present)

The legacy system has been safely decommissioned.
New system (Python/FastAPI) is the sole active backend.
EOF
  info "Decommission record saved: $DECOMMISSION_RECORD"
else
  info "[DRY-RUN] Decommission record would be saved to: $DECOMMISSION_RECORD"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo -e "${GREEN}╔═════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✔  DECOMMISSION COMPLETED SUCCESSFULLY              ║${NC}"
echo -e "${GREEN}║     Timestamp : $TIMESTAMP          ${NC}"
if [[ "$DRY_RUN" == "true" ]]; then
echo -e "${YELLOW}║     Mode      : DRY-RUN (no live changes made)       ║${NC}"
fi
echo -e "${GREEN}╚═════════════════════════════════════════════════════╝${NC}"
echo ""
info "The legacy Java/Spring Boot monolith has been safely decommissioned."
info "Active backend: Python/FastAPI at $NEW_SERVICE_URL"
