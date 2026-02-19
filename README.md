# MCP Integration Lab

A hands-on, instructor-led lab for building and debugging a Model Context Protocol (MCP) server that connects an AI agent to a mock enterprise search API.

## What You'll Learn

- **MCP fundamentals** — client-server architecture, tool discovery, JSON-RPC, and stdio transport
- **Build an MCP server** — implement a `kb_search(query, top_k)` tool using the Python SDK (FastMCP)
- **Validate grounded answers** — confirm results include citations, relevance scores, and permission boundaries
- **Troubleshoot integration failures** — use MCP Inspector to isolate faults across client, server, and endpoint layers

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────────────┐
│   AGENT     │───>│ MCP Client  │───>│ MCP Server  │───>│ Mock Search API  │
│  User prompt│    │ Tool        │    │ kb_search() │    │ HTTP endpoint    │
│  LLM reason │    │ discovery   │    │ Schema +    │    │ Ranked results   │
│             │    │ JSON-RPC    │    │ trust       │    │                  │
└─────────────┘    └─────────────┘    └─────────────┘    └──────────────────┘
```

The MCP server exposes a `kb_search` tool that queries a local mock enterprise search API (8 documents across 3 topics: renewals, onboarding, and security). Results include relevance scores, citations, and ACL permission groups.

## Prerequisites

| Component | Required Version | Check Command |
|-----------|-----------------|---------------|
| Python    | 3.12+           | `python3.12 --version` |
| Node.js   | 18+             | `node --version` |
| npm / npx | 9+              | `npx --version` |

## Quick Start

### 1. Setup

```bash
cd mcp-lab
bash setup.sh
```

This installs dependencies, pre-caches MCP Inspector, and runs 3 end-to-end validation tests. All 3 should show **PASS**.

### 2. Start the Mock Search API

```bash
python3.12 mock_search_api.py
```

### 3. Test with curl (in a second terminal)

```bash
curl -s "http://localhost:8080/search?q=renewal+process&top_k=3" | python3 -m json.tool
```

### 4. Discover Tools via MCP Inspector

```bash
npx @modelcontextprotocol/inspector --cli \
  --config inspector-config.json \
  --server enterprise-search \
  --method tools/list
```

### 5. Call the Tool through MCP

```bash
npx @modelcontextprotocol/inspector --cli \
  --config inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=What is our Q4 renewal process' \
  --tool-arg 'top_k=3'
```

## File Structure

```
mcp-lab/
├── server.py               # MCP server with kb_search tool (stdio transport)
├── mock_search_api.py       # Mock enterprise search API (local HTTP on port 8080)
├── lambda_function.py       # Same search logic packaged for AWS Lambda (reference)
├── inspector-config.json    # MCP Inspector config for CLI mode
├── setup.sh                 # One-command setup + validation
├── teardown.sh              # Kill all running processes + clean temp files
├── reset-lab.sh             # Teardown + setup (between lab sessions)
├── 00-PRE-SETUP-GUIDE.md    # Facilitator pre-setup instructions
├── 01-LAB-GUIDE.md          # Learner-facing lab guide (7 sections)
└── TALK-TRACK.md            # Full presenter talk track with timing
```

## Lab Sections

| # | Section | Duration |
|---|---------|----------|
| 1 | Customer Story and Architecture | ~8 min |
| 2 | Environment Verification | ~5 min |
| 3 | Explore the Mock Search API | ~15 min |
| 4 | Build the MCP Server | ~15 min |
| 5 | End-to-End Query Validation | ~15 min |
| 6 | Troubleshooting and Debugging | ~12 min |
| 7 | Customer Positioning Wrap-Up | ~10 min |

**Total: 60-90 minutes**

## Troubleshooting

| Problem | Symptom | Fix |
|---------|---------|-----|
| Endpoint URL wrong | Tool call fails with connection error | Correct the `ENDPOINT` in `server.py` |
| stdout corrupted | Server breaks randomly | Ensure all `print()` calls use `file=sys.stderr` |
| Mock API not running | Connection refused | Start it: `python3.12 mock_search_api.py` |
| Port 8080 in use | Address already in use | `pkill -f mock_search_api; sleep 2; python3.12 mock_search_api.py` |
| Everything broken | Multiple failures | `bash reset-lab.sh` |

## Production Considerations

This lab uses stdio transport and a local HTTP server for simplicity. For production deployments, add:

- **OAuth 2.1 authorization** for the MCP transport
- **Streamable HTTP transport** instead of stdio (supports multiple clients)
- **Origin header validation** for HTTP transports
- **Least-privilege tool scoping** — agents only see tools they need
- **HTTPS endpoint** — Lambda Function URL or API Gateway instead of localhost
- **Prompt injection controls** — input validation at the tool boundary

## License

MIT
