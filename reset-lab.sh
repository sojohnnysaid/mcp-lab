#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# reset-lab.sh — Kill all processes and re-validate the lab from scratch
# Run this between lab sessions for a clean start
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "======================================================="
echo "  MCP Lab Reset — Clean Slate for Next Session"
echo "======================================================="
echo ""

echo "--- Phase 1: Teardown ---"
echo ""
bash "$SCRIPT_DIR/teardown.sh"

echo ""
echo "--- Phase 2: Setup & Validate ---"
echo ""
bash "$SCRIPT_DIR/setup.sh"

echo ""
echo "Reset complete. Lab is ready for the next cohort."
