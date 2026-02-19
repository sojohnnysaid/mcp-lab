# MCP Integration Lab: Agent Calling a Mock Enterprise Search API via MCP

**Duration:** 60-90 minutes | **Delivery:** Instructor-led, hands-on | **Environment:** AWS Cloud9

---

## What You Will Learn

By the end of this lab, you will be able to:

1. **Explain MCP's mental model** — client-server architecture, the three capability primitives (tools, resources, prompts), and where schemas live
2. **Deploy a mock enterprise search API** — stand up a local endpoint with a realistic `/search` contract returning structured metadata
3. **Wire an MCP server tool** — implement `kb_search(query, top_k)` using the Python SDK that calls the endpoint and returns structured results
4. **Validate grounded answers** — confirm results include citations, relevance scores, and permission boundaries
5. **Troubleshoot integration failures** — use MCP Inspector and server logs to isolate faults across client, server, and endpoint layers

---

## Section 1 — Customer Story and Architecture (~8 min, Discussion)

### The Challenge

> "Your customer's agents need controlled access to real enterprise systems. How do you connect them without building a bespoke integration for every system?"

### The Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌──────────────────┐
│   AGENT     │───>│ MCP Client  │───>│ MCP Server  │───>│ Mock Search API  │
│  User prompt│    │ Tool        │    │ kb_search() │    │ HTTP endpoint    │
│  LLM reason │    │ discovery   │    │ Schema +    │    │ Ranked results   │
│             │    │ JSON-RPC    │    │ trust       │    │                  │
└─────────────┘    └─────────────┘    └─────────────┘    └──────────────────┘
                                                                  │
                   Grounded Answer  <── Structured  <── Ranked    │
                   + Citations          Payload         Results JSON
```

### Key Concepts

| Concept | What It Does |
|---------|-------------|
| **MCP Server** | Exposes tools, resources, and prompts to clients via a standardized schema |
| **MCP Client** | Discovers server capabilities and calls tools with structured arguments |
| **Tools** | Callable functions for API calls and side effects (**our lab focus**) |
| **Resources** | Read-only data artifacts (file-like context) — discussed, not implemented |
| **Prompts** | Reusable prompt templates — discussed, not implemented |
| **JSON-RPC** | Message encoding format over the transport |
| **stdio transport** | Client launches server as a subprocess (this lab) |
| **Streamable HTTP** | Server runs independently, multiple clients (production) |

### Discussion Questions

- Where does the tool schema live? Who controls what the agent can call?
- Why does a standard protocol matter over custom integrations?
- How many different APIs does your largest customer integrate with today?

---

## Section 2 — Verify Your Environment (~5 min)

Open a terminal in Cloud9 and confirm your toolchain:

```bash
python3.12 --version        # Python 3.12.x
node --version               # v18+
python3.12 -c "from importlib.metadata import version; print(version('mcp'))"
```

**Done looks like:** All commands return valid output. No errors.

---

## Section 3 — Explore the Mock Enterprise Search API (~15 min)

The mock API simulates an enterprise search system (like Glean). It has 8 canned documents across 3 topics: **renewals**, **onboarding**, and **security**.

### 3.1 — Review the API Contract

```
GET /search?q=<query>&top_k=<number>

Response:
{
  "query": "quarterly renewal process",
  "results": [
    {
      "doc_id": "DOC-042",
      "title": "Q4 2024 Renewal Playbook",
      "snippet": "Standard renewal process begins 90 days...",
      "url": "https://wiki.acme.co/renewals/q4-2024",
      "score": 0.94,
      "acl_group": "sales-team"
    }
  ]
}
```

Each result includes:
- **doc_id** — unique document identifier
- **title** / **snippet** — the content the agent will cite
- **score** — relevance score (0-1)
- **acl_group** — permission boundary (who can see this document)

### 3.2 — Start the Mock API

Open **Terminal 1** and start the mock search server:

```bash
python3.12 ~/environment/mcp-lab/mock_search_api.py
```

You should see:
```
Mock Search API running on http://localhost:8080
  Try: curl http://localhost:8080/search?q=renewal+process&top_k=3
```

> **Keep this terminal running.** Open a **second terminal** (click the `+` tab in Cloud9) for the remaining steps.

### 3.3 — Test the API with curl

In **Terminal 2**, run test queries against all three topics:

```bash
# Query 1: Renewals
curl -s "http://localhost:8080/search?q=renewal+process&top_k=3" | python3 -m json.tool

# Query 2: Security
curl -s "http://localhost:8080/search?q=security+incident+response&top_k=3" | python3 -m json.tool

# Query 3: Onboarding
curl -s "http://localhost:8080/search?q=onboarding+new+employee&top_k=3" | python3 -m json.tool
```

### 3.4 — Read the API Code

Open `mcp-lab/mock_search_api.py` in the Cloud9 editor. Notice:

- **8 documents** with realistic titles, snippets, URLs, and ACL groups
- **Keyword-overlap scoring** — deterministic and reproducible
- **top_k parameter** — limits results just like a real search API
- **acl_group field** — represents enterprise permission boundaries

> **Production note:** In a real deployment, this would be an HTTPS endpoint (Lambda Function URL, API Gateway, or any REST API). The MCP server code is identical — only the `ENDPOINT` URL changes.

**Done looks like:** `curl` returns deterministic JSON for all three query topics.

---

## Section 4 — Build the MCP Server (~15 min)

This is the core of the lab. You will explore an MCP server using the official Python SDK (FastMCP) that exposes a `kb_search` tool.

### 4.1 — Read the Server Code

Open `mcp-lab/server.py` in the Cloud9 editor. Walk through each section:

```python
from mcp.server.fastmcp import FastMCP
import httpx, sys, json, os

# The endpoint URL for the mock search API
ENDPOINT = os.environ.get("SEARCH_ENDPOINT", "http://localhost:8080")

# Create the MCP server
mcp = FastMCP("enterprise-search")

# Define a tool
@mcp.tool()
async def kb_search(query: str, top_k: int = 3) -> str:
    """Search the enterprise knowledge base."""
    url = f"{ENDPOINT}/search?q={query}&top_k={top_k}"

    # CRITICAL: Log to stderr, NEVER stdout
    print(f"[kb_search] Calling: {url}", file=sys.stderr)

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()

    return json.dumps(resp.json(), indent=2)

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### Key Points to Discuss

| Concept | Detail |
|---------|--------|
| **`@mcp.tool()` decorator** | Registers the function as a discoverable MCP tool with auto-generated schema |
| **Type hints** | `query: str, top_k: int = 3` become the tool's JSON Schema automatically |
| **Docstring** | Becomes the tool description that agents use to decide when to call it |
| **`transport="stdio"`** | Client launches server as a subprocess; JSON-RPC flows over stdin/stdout |
| **stderr for logging** | stdout is sacred — only JSON-RPC frames. All logging goes to stderr |

### 4.2 — Discover the Tool with MCP Inspector

MCP Inspector is the debugging tool for protocol-level testing. Use it to verify the server.

**List tools** (in Terminal 2, while mock API is running in Terminal 1):

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/list
```

You should see:
- Tool name: `kb_search`
- Input schema: `query` (string, required), `top_k` (integer, optional, default 3)

### 4.3 — Call the Tool through MCP

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=What is our Q4 renewal process' \
  --tool-arg 'top_k=3'
```

You should see structured JSON with ranked results flowing back through the MCP protocol.

**Done looks like:** MCP Inspector discovers `kb_search`, shows input schema, and returns structured search results.

---

## Section 5 — End-to-End Query Validation (~15 min)

Run the SE scenario query and validate three dimensions.

### 5.1 — Run the Scenario Query

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=What is our Q4 renewal process' \
  --tool-arg 'top_k=3'
```

### 5.2 — Validate the Results

Check each dimension:

| Dimension | What to Check | What You Should See |
|-----------|--------------|-------------------|
| **RELEVANCE** | Do the top results match the query intent? | DOC-042 (Renewal Playbook) should be #1 with highest score |
| **GROUNDING** | Do results contain citable content? | Each result has `title`, `snippet`, and `url` an agent can reference |
| **PERMISSIONS** | Do results include access boundaries? | `acl_group` field shows which team can see each document |

### 5.3 — Try Different Queries

Test the other topics and observe how results change:

```bash
# Security topic — notice acl_group is "security-team"
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=data classification policy' \
  --tool-arg 'top_k=2'

# Onboarding topic — notice mixed acl_groups
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=customer onboarding' \
  --tool-arg 'top_k=3'
```

### 5.4 — Trace the Full Flow

Map what happened at each layer:

```
User query: "What is our Q4 renewal process?"
    │
    ▼
Agent selects kb_search tool (based on tool description)
    │
    ▼
MCP Client sends JSON-RPC call via stdio
    │
    ▼
MCP Server receives call, runs kb_search()
    │
    ▼
kb_search() calls mock search API via HTTP
    │
    ▼
API returns ranked JSON results
    │
    ▼
MCP Server returns structured payload to client
    │
    ▼
Agent synthesizes grounded answer with citations
```

**Done looks like:** You can explain where grounding happens and point to which document snippet would support each claim in an agent's response.

---

## Section 6 — Troubleshooting and Debugging (~12 min)

Deliberately break one layer, then fix it. This builds the confidence you need to troubleshoot during live demos and customer POVs.

### Triage Pattern: "Client, Server, Endpoint"

1. **Does MCP Inspector see the tool?** → If not, it's a **server** problem
2. **Does the tool call return data?** → If not, it's an **endpoint** problem
3. **Does the agent use the data correctly?** → If not, it's a **client/agent** problem

### Exercise 1: Break the Endpoint URL

Open `server.py` and change the ENDPOINT to a bad URL:

```python
ENDPOINT = os.environ.get("SEARCH_ENDPOINT", "http://localhost:9999")
```

Run a tool call:

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=renewal process'
```

**What happens?** The tool is discoverable (server is fine) but the call fails (endpoint problem).

**Fix:** Restore the correct URL (`http://localhost:8080`).

### Exercise 2: Break stdout (The #1 Real-World Failure)

Add a `print()` to stdout in the tool function (without `file=sys.stderr`):

```python
@mcp.tool()
async def kb_search(query: str, top_k: int = 3) -> str:
    print(f"DEBUG: searching for {query}")   # <-- BUG: goes to stdout!
    ...
```

**What happens?** The server may appear to "break randomly" because the print statement corrupts the JSON-RPC stream on stdout.

**Fix:** Always use `print(..., file=sys.stderr)` for logging in stdio servers.

### Exercise 3: Stop the Mock API

Go to Terminal 1 and press `Ctrl+C` to stop the mock API. Then try a tool call.

**What happens?** The tool is discoverable but the call fails with a connection error.

**Fix:** Restart the mock API: `python3.12 ~/environment/mcp-lab/mock_search_api.py`

### Failure Reference

| Break This | Symptom | Debug With | Fix |
|-----------|---------|-----------|-----|
| Endpoint URL | Tool call fails or returns error | MCP Inspector + server stderr | Correct the ENDPOINT variable |
| stdout (print without stderr) | Server breaks randomly | Check for `print()` without `file=sys.stderr` | Redirect all logs to stderr |
| Stop mock API | Connection refused | curl the endpoint directly | Restart the API server |
| Tool schema | Tool discovered but wrong args | MCP Inspector `tools/list` | Align tool signature |

**Done looks like:** You can isolate the fault domain using the three-layer triage pattern.

---

## Section 7 — Customer Positioning Wrap-Up (~10 min)

### Two-Minute Positioning Narrative

Practice with a partner:

> "MCP is a standard interface for tool discovery and structured tool calls — like a universal port for agent integrations. Instead of building a custom connector for every system, you declare your tools once and any MCP-compatible agent can discover and use them.
>
> We ground responses in retrieved sources, then generate. That means every answer comes with citations you can verify. And enterprise permissions stay intact — the agent only sees what the user is allowed to see."

### One-Minute "How It Works" Explanation

> "The agent discovers available tools through MCP's schema. When a user asks a question, the agent selects the right tool, sends a structured call through JSON-RPC, and the MCP server calls the enterprise search API. Results flow back with relevance scores and citations. The agent uses those to generate a grounded answer — no hallucination, just real enterprise data."

### Production Delta Discussion

SEs will be asked: **"Is this production-ready?"**

Answer confidently: "The protocol is production-ready. For your environment, we'd add:

- **OAuth 2.1 authorization** for the MCP transport
- **Streamable HTTP transport** instead of stdio (supports multiple clients)
- **Origin header validation** for HTTP transports
- **Least-privilege tool scoping** — agents only see tools they need
- **HTTPS endpoint** — Lambda Function URL or API Gateway instead of localhost
- **Prompt injection controls** — input validation at the tool boundary"

---

## Quick Reference Commands

```bash
# Start the mock API (Terminal 1)
python3.12 ~/environment/mcp-lab/mock_search_api.py

# Test the mock API directly (Terminal 2)
curl -s "http://localhost:8080/search?q=renewal+process&top_k=3" | python3 -m json.tool

# List MCP tools
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/list

# Call a tool through MCP
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=YOUR QUERY HERE' \
  --tool-arg 'top_k=3'
```

---

## Success Criteria

- [ ] **End-to-end success:** Run a query through MCP to the mock search API and receive ranked, citation-backed results
- [ ] **Vocabulary fluency:** Describe the flow using correct terms — tool schema, JSON-RPC, stdio transport, MCP Inspector
- [ ] **Production awareness:** Articulate the production delta — auth, Origin validation, least privilege, Streamable HTTP
- [ ] **Customer readiness:** Deliver a two-minute positioning narrative connecting MCP to real customer integration pain
