#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup.sh — Provision the MCP lab environment
# Installs dependencies, validates the mock API and MCP server work end-to-end
# ---------------------------------------------------------------------------
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
API_PORT=8080

echo "============================================"
echo " MCP Lab Setup"
echo "============================================"
echo ""

# ----- Prerequisites check -----
echo "[1/6] Checking prerequisites..."
FAIL=0
command -v node       >/dev/null 2>&1 || { echo "  ERROR: node not found."; FAIL=1; }
command -v aws        >/dev/null 2>&1 || { echo "  ERROR: aws CLI not found."; FAIL=1; }
if [ "$FAIL" -eq 1 ]; then echo "Fix the above and re-run."; exit 1; fi
echo "      node, aws CLI — OK"

# ----- Install Python 3.12 if needed -----
echo "[2/6] Checking Python 3.12..."
if command -v python3.12 >/dev/null 2>&1; then
  echo "      python3.12 already installed — OK"
else
  echo "      Installing python3.12..."
  sudo dnf install -y python3.12 python3.12-pip >/dev/null 2>&1
  echo "      Installed."
fi

# ----- Python packages -----
echo "[3/6] Installing Python packages (mcp, httpx)..."
python3.12 -m pip install --user --quiet mcp httpx 2>&1 | tail -1 || true
python3.12 -c "from importlib.metadata import version; print(f'      mcp {version(\"mcp\")} — OK')"

# ----- Pre-cache MCP Inspector -----
echo "[4/6] Pre-caching MCP Inspector..."
npx @modelcontextprotocol/inspector --help >/dev/null 2>&1 && echo "      Cached — OK" || echo "      WARNING: could not cache Inspector"

# ----- Write inspector-config.json -----
echo "[5/6] Writing inspector-config.json..."
cat > "$SCRIPT_DIR/inspector-config.json" <<JSONEOF
{
  "mcpServers": {
    "enterprise-search": {
      "command": "python3.12",
      "args": ["${SCRIPT_DIR}/server.py"]
    }
  }
}
JSONEOF
echo "      Done."

# ----- Validation -----
echo "[6/6] Validating end-to-end..."
echo ""

# Start mock API in background for testing
pkill -f "mock_search_api.py" 2>/dev/null || true
sleep 1
nohup python3.12 "$SCRIPT_DIR/mock_search_api.py" $API_PORT > /tmp/mock-api.log 2>&1 &
MOCK_PID=$!
sleep 2

# Test 1: curl the mock API
echo "  Test 1 — curl mock API (renewals):"
RESULT=$(curl -s "http://localhost:${API_PORT}/search?q=renewal+process&top_k=2" 2>/dev/null || echo "FAIL")
if echo "$RESULT" | grep -q "DOC-042"; then
  COUNT=$(echo "$RESULT" | python3 -c "import sys,json; print(len(json.loads(sys.stdin.read())['results']))" 2>/dev/null || echo "0")
  echo "    PASS — got $COUNT results"
else
  echo "    FAIL — could not reach mock API: $RESULT"
  echo "    Make sure port $API_PORT is available."
fi

# Test 2: MCP Inspector tool discovery
echo "  Test 2 — MCP Inspector tools/list:"
TOOLS=$(npx @modelcontextprotocol/inspector --cli \
  --config "$SCRIPT_DIR/inspector-config.json" \
  --server enterprise-search \
  --method tools/list 2>/dev/null || echo "FAIL")
if echo "$TOOLS" | grep -q "kb_search"; then
  echo "    PASS — kb_search tool discovered"
else
  echo "    FAIL — tool not found"
fi

# Test 3: MCP Inspector tool call
echo "  Test 3 — MCP Inspector tools/call (end-to-end):"
CALL_RESULT=$(npx @modelcontextprotocol/inspector --cli \
  --config "$SCRIPT_DIR/inspector-config.json" \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=security incident' \
  --tool-arg 'top_k=2' 2>/dev/null || echo "FAIL")
if echo "$CALL_RESULT" | grep -q "DOC-202"; then
  echo "    PASS — got Incident Response Runbook (DOC-202)"
else
  echo "    FAIL — unexpected result"
fi

# Stop mock API (learners will start it themselves)
kill $MOCK_PID 2>/dev/null || true

echo ""
echo "============================================"
echo " Setup complete!"
echo ""
echo " To start the lab:"
echo "   1. Start the mock API:   python3.12 $SCRIPT_DIR/mock_search_api.py"
echo "   2. Open a new terminal"
echo "   3. Follow the lab guide: $SCRIPT_DIR/01-LAB-GUIDE.md"
echo "============================================"
