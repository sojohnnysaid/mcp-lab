# MCP Integration Lab — Pre-Setup Guide (Facilitator)

Everything that must be done **before** learners arrive. Run these steps once per lab environment.

---

## Environment Requirements

| Component       | Required Version | Check Command              |
|-----------------|-----------------|----------------------------|
| Python          | 3.12+           | `python3.12 --version`     |
| Node.js         | 18+             | `node --version`           |
| npm / npx       | 9+              | `npx --version`            |

> This lab was built on **AWS Cloud9** (Amazon Linux 2023). If using a different environment, adapt the install commands accordingly.

---

## Option A: One-Command Setup (Recommended)

```bash
cd ~/environment/mcp-lab
bash setup.sh
```

This script:
1. Installs Python 3.12 if missing
2. Installs `mcp` and `httpx` Python packages
3. Pre-caches MCP Inspector (npx)
4. Writes `inspector-config.json`
5. Runs 3 end-to-end validation tests

All 3 tests should show **PASS**.

---

## Option B: Manual Setup

### Step 1 — Install Python 3.12

```bash
sudo dnf install -y python3.12 python3.12-pip
python3.12 --version
```

### Step 2 — Install MCP SDK and Dependencies

```bash
python3.12 -m pip install --user mcp httpx
```

### Step 3 — Pre-cache MCP Inspector

```bash
npx @modelcontextprotocol/inspector --help
```

### Step 4 — Test the Mock API

Start the mock API in one terminal:

```bash
python3.12 ~/environment/mcp-lab/mock_search_api.py
```

In a second terminal, test:

```bash
curl -s "http://localhost:8080/search?q=renewal+process&top_k=3" | python3 -m json.tool
curl -s "http://localhost:8080/search?q=security+incident&top_k=2" | python3 -m json.tool
curl -s "http://localhost:8080/search?q=onboarding+new+employee&top_k=2" | python3 -m json.tool
```

### Step 5 — Test MCP Server End-to-End

(Mock API must be running in another terminal)

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/list

npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=renewal process' \
  --tool-arg 'top_k=3'
```

---

## Between Lab Sessions

Reset everything for the next cohort:

```bash
cd ~/environment/mcp-lab
bash reset-lab.sh
```

Or manually:

```bash
bash teardown.sh    # kills all running processes
bash setup.sh       # re-validates everything
```

---

## Pre-Setup Checklist

- [ ] Python 3.12 installed
- [ ] `mcp` and `httpx` packages installed for python3.12
- [ ] MCP Inspector pre-cached via npx
- [ ] `mock_search_api.py` starts and responds to curl on port 8080
- [ ] `server.py` ENDPOINT points to `http://localhost:8080`
- [ ] MCP Inspector discovers `kb_search` tool
- [ ] MCP Inspector tool call returns results end-to-end
- [ ] `setup.sh` shows 3/3 PASS

---

## File Inventory

```
mcp-lab/
├── mock_search_api.py      # Mock search API (local HTTP server, port 8080)
├── server.py               # MCP server with kb_search tool (stdio transport)
├── inspector-config.json   # MCP Inspector config for CLI mode
├── lambda_function.py      # Lambda-compatible version (for AWS deployment)
├── setup.sh                # One-command setup + validation
├── teardown.sh             # Kill all processes + clean temp files
├── reset-lab.sh            # Teardown + setup (between sessions)
├── 00-PRE-SETUP-GUIDE.md   # This file
└── 01-LAB-GUIDE.md         # Learner-facing lab guide
```

---

## Architecture Note

The lab uses a **local HTTP server** (`mock_search_api.py` on port 8080) instead of AWS Lambda + Function URL. This:

- **Eliminates AWS IAM/permission issues** that can eat lab time
- **Starts instantly** — no deployment wait
- **Teaches the same pattern** — MCP server calls an HTTP search endpoint
- **Maps to production** — in production, the endpoint would be a Lambda Function URL, API Gateway, or any HTTPS API. The MCP server code is identical either way; only the `ENDPOINT` variable changes.

The `lambda_function.py` is included for reference — it contains the same search logic packaged for AWS Lambda deployment (used in the facilitator's "production delta" discussion).
