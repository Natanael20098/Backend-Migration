#!/usr/bin/env bash
# run_tests_with_reports.sh
#
# Runs all non-integration tests (unit + in-process integration + security
# audit) and produces HTML and JUnit XML reports in the reports/ directory.
#
# Usage:
#   cd backend
#   bash scripts/run_tests_with_reports.sh
#
# Output files:
#   reports/integration-report.html    — full test run HTML report
#   reports/integration-report.xml     — JUnit XML (for CI/CD systems)
#   reports/security-audit.html        — security-only HTML report
#   reports/security-audit.xml         — security-only JUnit XML
#
# Exit code: 0 if all tests pass, non-zero otherwise.

set -euo pipefail

REPORTS_DIR="$(cd "$(dirname "$0")/.." && pwd)/reports"
mkdir -p "$REPORTS_DIR"

echo "================================================================"
echo "  Running Integration Tests (all endpoints, in-process)"
echo "================================================================"
python3 -m pytest \
    tests/integration/test_all_endpoints_in_process.py \
    tests/unit/ \
    -v \
    --tb=short \
    -m "not integration" \
    --html="$REPORTS_DIR/integration-report.html" \
    --self-contained-html \
    --junitxml="$REPORTS_DIR/integration-report.xml"

INTEGRATION_EXIT=$?

echo ""
echo "================================================================"
echo "  Running Security Audit Tests (OWASP-aligned)"
echo "================================================================"
python3 -m pytest \
    tests/security/ \
    tests/unit/test_security.py \
    -v \
    --tb=short \
    --html="$REPORTS_DIR/security-audit.html" \
    --self-contained-html \
    --junitxml="$REPORTS_DIR/security-audit.xml"

SECURITY_EXIT=$?

echo ""
echo "================================================================"
echo "  Reports written to: $REPORTS_DIR"
echo "    integration-report.html"
echo "    integration-report.xml"
echo "    security-audit.html"
echo "    security-audit.xml"
echo "================================================================"

if [ "$INTEGRATION_EXIT" -ne 0 ] || [ "$SECURITY_EXIT" -ne 0 ]; then
    echo "FAILURE: one or more test suites reported failures."
    exit 1
fi

echo "SUCCESS: all tests passed."
exit 0
