#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# teardown.sh — Stop all running lab processes and clean temp files
# ---------------------------------------------------------------------------
set -euo pipefail

echo "============================================"
echo " MCP Lab Teardown"
echo "============================================"

# 1. Stop mock search API
echo "[1/3] Stopping mock search API..."
pkill -f "mock_search_api.py" 2>/dev/null && echo "      Stopped." || echo "      Not running."

# 2. Stop any lingering MCP server processes
echo "[2/3] Stopping MCP server processes..."
pkill -f "server.py" 2>/dev/null && echo "      Stopped." || echo "      Not running."

# 3. Clean temp files
echo "[3/3] Cleaning temp files..."
rm -f /tmp/mock-api.log /tmp/mock-search.zip /tmp/mcp-stderr.log /tmp/mcp-stdout.log
echo "      Done."

echo ""
echo "Teardown complete."
