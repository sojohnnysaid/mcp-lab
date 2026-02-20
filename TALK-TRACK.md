# MCP Integration Lab — Presenter Talk Track

**Presenter:** John Yzaguirre
**Total Time:** 60–90 minutes (adjustable)
**Format:** Instructor-led, hands-on, live terminal

> Every command, every talking point, every transition is here in the order you will deliver it. Commands are in code blocks. Talk track is in plain text. Facilitator notes are in blockquotes.

---

## PRE-SETUP (Before anyone arrives)

Do these steps **at least 30 minutes before the session** to avoid surprises.

### Open Cloud9

1. Log into the AWS Console
2. Navigate to Cloud9 > Open IDE
3. Maximize the terminal pane

### Run the automated setup

```bash
cd ~/environment/mcp-lab
bash setup.sh
```

**Confirm you see 3/3 PASS at the bottom.** If any test fails, re-run `bash reset-lab.sh`.

### Prepare your terminals

1. **Terminal 1** — will run the mock search API (keep this visible)
2. **Terminal 2** — will be your main working terminal for commands
3. Have `mock_search_api.py` and `server.py` open in editor tabs

### Start the mock API

In Terminal 1:

```bash
python3.12 ~/environment/mcp-lab/mock_search_api.py
```

Confirm it prints:
```
Mock Search API running on http://localhost:8080
```

### Quick smoke test (Terminal 2)

```bash
curl -s "http://localhost:8080/search?q=renewal&top_k=2" | python3 -m json.tool | jq
```

Confirm you see JSON results. You are ready.

> **Facilitator note:** If you need to restart fresh at any point during the lab, run `bash ~/environment/mcp-lab/reset-lab.sh` and restart the mock API.

---
---

## SECTION 1 — Intro and Customer Story (~8 min)

### 1.1 — Open with the problem

**SAY:**

"Let me set the scene with a customer conversation. Imagine you're sitting across from a VP of IT at a Fortune 500 company. They've rolled out an AI assistant internally — maybe it's connected to Slack, maybe it's a chat widget on the intranet. And they ask you:

*'Our AI assistant hallucinates. It makes up policy details that don't exist. How do we make it use our real internal documents instead of guessing?'*

That's the problem we're solving today."

**PAUSE — let that land.**

### 1.2 — Introduce MCP as the solution pattern

**SAY:**

"The answer is a pattern called *retrieval-augmented generation* — RAG. Instead of letting the AI make things up, we teach it to *search first, then answer*. It retrieves real documents from your enterprise systems, then generates a response grounded in those sources — with citations you can verify.

But here's the next question: *how does the agent actually connect to those enterprise systems?*

That's where MCP comes in. Model Context Protocol. It's a standard interface — think of it like USB-C for AI integrations. One protocol, many enterprise systems. Instead of building a custom connector for every data source, you declare your tools once and any MCP-compatible agent can discover and use them."

### 1.3 — Draw the four-box architecture

> **Facilitator note:** Draw this on a whiteboard, or point to it on screen. Walk left to right slowly.

**SAY (while drawing/showing):**

```
Agent / UI  →  MCP Client  →  MCP Server  →  Enterprise Search API
```

"Four boxes. Let's walk through each one.

1. **Agent / UI** — This is the user-facing layer. A user types a question like 'What is our Q4 renewal process?' The LLM reasons about what it needs and decides to use a search tool.

2. **MCP Client** — This is the transport layer. It discovers what tools are available on the server, then sends a structured JSON-RPC call. Think of it as the wiring.

3. **MCP Server** — This is where *we* define our tools. We'll build one today called `kb_search`. It has a schema — what arguments it accepts, what it returns. The server is the trust boundary. It controls what the agent can call.

4. **Enterprise Search API** — The actual data source. Today it's a mock. In production, this could be Glean, an internal wiki, Confluence, ServiceNow — any system of record.

The response flows back: the API returns ranked results, the MCP server passes them through, and the agent generates a grounded answer with citations pointing to real documents."

### 1.4 — Introduce the three MCP primitives

**SAY:**

"MCP has three primitives. We're going to focus on one:

- **Tools** — Callable functions. The agent can invoke them. This is what we're building today: `kb_search`.
- **Resources** — Read-only data. Think file-like context the server can provide. We won't implement these today, but they exist.
- **Prompts** — Reusable prompt templates exposed by the server. Also out of scope today.

Tools are the most common primitive in customer conversations because they map directly to *'agent calls enterprise system.'* That's the story we need to tell."

### 1.5 — Ground it in their world

**ASK THE GROUP:**

"Quick question — think of your largest customer. How many different APIs or internal systems do their agents need to talk to? Raise a hand if it's more than five."

> **Facilitator note:** This grounds the abstract protocol in real customer pain. MCP's value is proportional to the number of systems an agent needs to reach.

**SAY:**

"Every one of those integrations is either a custom connector someone has to maintain, or it's a standard protocol connection that just works. That's the MCP value prop. Let's build it."

**TRANSITION:** "Alright, let's verify our environment is ready and start building."

---

## SECTION 2 — Environment Verification (~5 min)

### 2.1 — Check the toolchain

**SAY:**

"We're working in AWS Cloud9 — a browser-based IDE with a built-in terminal. Everything is pre-installed. Let's confirm."

**RUN in Terminal 2:**

```bash
python3.12 --version
```

**SAY:** "Python 3.12 — the MCP Python SDK requires 3.10 or higher."

```bash
node --version
```

**SAY:** "Node.js — we need this for MCP Inspector, our debugging tool."

```bash
python3.12 -c "from importlib.metadata import version; print(version('mcp'))"
```

**SAY:** "And the MCP SDK itself is installed. We're using the official Python SDK — FastMCP — which is the same SDK in the MCP documentation and tutorials."

### 2.2 — Confirm the mock API is running

**SAY:** "I already started our mock search API in the other terminal. Let's confirm it responds."

```bash
curl -s "http://localhost:8080/health"
```

**Expected output:** `{"status":"ok"}`

**SAY:** "Good. The enterprise search endpoint is live. Let's explore it."

**TRANSITION:** "Now let's look at what this search API actually returns."

---

## SECTION 3 — Explore the Mock Enterprise Search API (~15 min)

### 3.1 — Explain the search contract

**SAY:**

"Our mock API simulates an enterprise search system — like what Glean provides. It has 8 canned documents across three topics: *renewals*, *onboarding*, and *security*. The API contract is simple: you send a query and a `top_k` parameter, and you get back ranked results."

**Show the contract (point to editor or recite):**

**SAY:**

"Each result has six fields. Let me highlight the ones that matter for customer conversations:

- `title` and `snippet` — this is what the agent will *cite* in its answer
- `score` — relevance ranking, so the agent knows which results to prioritize
- `url` — the source link for verification
- `acl_group` — *this is the big one*. This is the permission boundary. It tells you which team has access to this document. The agent should only surface results the user is authorized to see."

### 3.2 — Run the three demo queries

**SAY:** "Let's test all three topics. Watch how the results change."

**RUN — Renewals:**

```bash
curl -s "http://localhost:8080/search?q=renewal+process&top_k=3" | python3 -m json.tool
```

**POINT OUT:**
- "DOC-042, the Renewal Playbook, scores highest at 0.7"
- "All three results have `acl_group: sales-team`"
- "These are the exact results an agent would use to answer 'What is our Q4 renewal process?'"

**RUN — Security:**

```bash
curl -s "http://localhost:8080/search?q=security+incident+response&top_k=3" | python3 -m json.tool
```

**POINT OUT:**
- "The Incident Response Runbook scores 0.99 — very high confidence"
- "Notice `acl_group: security-team` — in a production system, only users in that group would see these results"
- "The third result is from a different topic entirely — onboarding — because it mentions 'security training.' The score is low. This is realistic: real search systems return cross-topic results too"

**RUN — Onboarding:**

```bash
curl -s "http://localhost:8080/search?q=onboarding+new+employee&top_k=3" | python3 -m json.tool
```

**POINT OUT:**
- "Mixed `acl_group` values: `all-employees`, `customer-success`, `sales-team`"
- "This is a great customer talking point: *different documents, different permissions, same query*"

### 3.3 — Look at the code (optional, time permitting)

> **Facilitator note:** Click into `mock_search_api.py` in the Cloud9 editor. Scroll to the DOCUMENTS list.

**SAY:**

"The data is deterministic — no randomness. This matters for a lab because every learner gets the same results, which makes debugging reproducible. In production, this would be a live search index."

**TRANSITION:** "The endpoint works. Now let's wire it into an MCP server."

---

## SECTION 4 — MCP Server Wiring (~15 min)

> This is the core of the lab. Slow down here.

### 4.1 — Open server.py in the editor

**SAY:**

"Let me show you the MCP server. This is the file that turns our search API into something an agent can discover and call through the Model Context Protocol."

> **Facilitator note:** Open `server.py` in the Cloud9 editor. Walk through it line by line.

### 4.2 — Walk through the code

**SAY (pointing to lines 1-13):**

"We import `FastMCP` from the official MCP Python SDK. We also import `httpx` — an async HTTP client — and the standard library modules we need."

**SAY (pointing to lines 15-23):**

"The `ENDPOINT` variable points to our mock API. Right now it's `localhost:8080`. In production, you'd change this to a Lambda Function URL, an API Gateway endpoint, or any HTTPS API. The MCP server code stays exactly the same — only this one line changes."

**SAY (pointing to line 25):**

"`FastMCP('enterprise-search')` — we create the server and give it a name. This name shows up in MCP Inspector and in client discovery."

**SAY (pointing to lines 28-52):**

"Here's the tool definition. Let me break this down because every line does something important:

- **`@mcp.tool()`** — This decorator registers the function as an MCP tool. The SDK automatically generates a JSON Schema from the function signature.

- **`async def kb_search(query: str, top_k: int = 3) -> str:`** — The type hints become the tool's input schema. `query` is required, `top_k` is optional with a default of 3. An agent reading this schema knows exactly what arguments to provide.

- **The docstring** — This becomes the tool description. It's what the LLM reads to decide *when* to use this tool. Write it like you're explaining the tool to a smart colleague.

- **`print(..., file=sys.stderr)`** — This is critical."

**PAUSE here. Make eye contact.**

**SAY:**

"This is the number one real-world failure mode for MCP servers using stdio transport. Let me explain why.

In stdio mode, the MCP client and server communicate over standard input and standard output. Stdout is *sacred* — it must only contain JSON-RPC frames. If you accidentally `print()` to stdout — a debug message, a status update, anything — you corrupt the JSON-RPC stream and the server breaks. Sometimes silently, sometimes randomly.

The fix is simple: always use `file=sys.stderr` for logging. We'll break this on purpose later so you can see what happens."

**SAY (pointing to lines 55-57):**

"`mcp.run(transport='stdio')` — This starts the server using stdio transport. The client will launch this script as a subprocess and communicate over stdin/stdout. No HTTP server, no OAuth, no ports. This is why stdio is perfect for a lab — zero infrastructure."

### 4.3 — Discover the tool with MCP Inspector

**SAY:**

"Now let's prove the tool is discoverable. MCP Inspector is an interactive debugging tool — it's the tool you'll actually use when troubleshooting customer POVs."

**RUN:**

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/list
```

**POINT OUT in the output:**

**SAY:**

"Look at this. The inspector started our MCP server, performed tool discovery, and found `kb_search`. See the `inputSchema`?

- `query`: type string, required
- `top_k`: type integer, default 3

This schema was generated automatically from our Python type hints. We didn't write any JSON Schema by hand. That's the FastMCP developer experience."

### 4.4 — Call the tool through MCP

**SAY:**

"Now the real test. Let's call the tool through the full MCP protocol — the same way a real agent would."

**RUN:**

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=What is our Q4 renewal process' \
  --tool-arg 'top_k=3'
```

**WAIT for output, then SAY:**

"There it is. The full chain just fired:

1. MCP Inspector launched our server as a subprocess
2. It sent a `tools/call` JSON-RPC request with the arguments
3. Our server ran `kb_search`, which called the mock API on localhost:8080
4. The API returned ranked results
5. The results flowed back through MCP as structured content

Look at the results — DOC-042, Renewal Playbook, score 0.7. DOC-043, Pricing Guidelines, score 0.6. These are the exact documents an agent would use to answer the question with citations."

**TRANSITION:** "Let's formalize what 'good results' means."

---

## SECTION 5 — End-to-End Query Validation (~15 min)

### 5.1 — Introduce the three validation dimensions

**SAY:**

"When a customer asks 'How do I know the integration is working?' — you need to answer with more than 'it returned something.' We validate on three dimensions."

**Recite or show the table:**

"1. **Relevance** — Do the top results match the query intent? Are the scores reasonable? This proves the search layer is working.

2. **Grounding** — Does the agent's answer reference the returned documents? Are there citations — not free-text hallucination? This is the core RAG value proposition.

3. **Permissions** — Do results include the `acl_group` field? Does the agent respect access boundaries? This is the enterprise governance story."

### 5.2 — Validate the renewals query

**SAY:** "Let's validate our renewal query against all three."

**RUN:**

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=What is our Q4 renewal process' \
  --tool-arg 'top_k=3'
```

**Walk through the output:**

**SAY:**

"**Relevance check:** DOC-042, Q4 2024 Renewal Playbook, is the top result with a score of 0.7. That matches the query intent perfectly. PASS.

**Grounding check:** Look at the snippet — 'Standard renewal process begins 90 days before contract expiration. Account team opens a renewal opportunity in Salesforce...' An agent can directly cite this. There's a `url` pointing to the wiki page. PASS.

**Permissions check:** `acl_group: sales-team` on all three results. If I were a user in the engineering team, a permission-aware system would filter these out. PASS.

This is how you define 'meaningful results' for a customer POV. Not just 'something came back' — you check relevance, grounding, and permissions."

### 5.3 — Cross-topic validation

**SAY:** "Let's try a security query and see how permissions change."

**RUN:**

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=security incident response' \
  --tool-arg 'top_k=3'
```

**POINT OUT:**

"The top result is the Incident Response Runbook — `acl_group: security-team`. The second is Data Classification — also `security-team`. But look at the third result — the Onboarding Checklist, `acl_group: all-employees`, score 0.1. It came back because the onboarding doc mentions 'security training.'

This is a great demo moment. You can say to the customer: *'See how the system returns results from different permission groups? In production, the agent would only show results matching the user's access level. The metadata is there — your authorization layer decides what to surface.'*"

**TRANSITION:** "Now let's learn to break things."

---

## SECTION 6 — Troubleshooting and Debugging (~12 min)

### 6.1 — Introduce the triage pattern

**SAY:**

"Every integration breaks. What matters is how fast you isolate the problem. I'm going to teach you a three-step triage pattern that works every time:

1. **Does MCP Inspector see the tool?** If not — it's a *server* problem.
2. **Does the tool call return data?** If not — it's an *endpoint* problem.
3. **Does the agent use the data correctly?** If not — it's a *client/agent* problem.

Client. Server. Endpoint. That's the order. Let's practice."

### 6.2 — Exercise: Break the endpoint URL

**SAY:** "First, let's break the endpoint. Open `server.py` in the editor."

> **Facilitator note:** Change line 22 from `"http://localhost:8080"` to `"http://localhost:9999"`

**SAY:** "I changed the endpoint to port 9999 — nothing is listening there. Now watch."

**RUN — Step 1 of triage:**

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/list
```

**SAY:** "Tool discovery still works. `kb_search` is visible. So the *server* is fine."

**RUN — Step 2 of triage:**

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=renewal process'
```

**SAY:** "The tool call fails — connection refused. Server is fine, but the *endpoint* is broken. Triage step 2 tells us exactly where the fault is."

**FIX:** Change the ENDPOINT back to `"http://localhost:8080"` in the editor.

> **Facilitator note:** Save the file.

**RUN (confirm fix):**

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=renewal process'
```

**SAY:** "Back in business. The fix took under a minute because we knew exactly which layer was broken."

### 6.3 — Exercise: Break stdout (the #1 failure mode)

**SAY:**

"Now the sneaky one. This is the bug that makes MCP servers 'break randomly' and drives people crazy the first time they hit it."

> **Facilitator note:** In `server.py`, add this line at the start of the `kb_search` function (line 40, before the existing `url = ...` line):
> ```python
>     print(f"DEBUG: searching for {query}")
> ```
> Notice: NO `file=sys.stderr`. This prints to stdout.

**SAY:**

"I just added a debug print statement. Looks harmless, right? Watch."

**RUN:**

```bash
npx @modelcontextprotocol/inspector --cli \
  --config ~/environment/mcp-lab/inspector-config.json \
  --server enterprise-search \
  --method tools/call \
  --tool-name kb_search \
  --tool-arg 'query=renewal process'
```

**SAY (after error or garbled output):**

"See? The server might error, hang, or return garbage. The print statement wrote `DEBUG: searching for renewal process` to *stdout*, right in the middle of the JSON-RPC stream. The client tried to parse it as JSON and choked.

The rule is simple: **stdout is sacred in stdio transport.** Only JSON-RPC frames. Every log, every debug message, goes to stderr."

**FIX:** Remove the debug print line (or add `file=sys.stderr`).

**SAY:**

"In a customer environment, search for any `print(` that doesn't have `file=sys.stderr`. That's your bug. Every time."

### 6.4 — Summarize the failure table

**SAY:**

"Quick reference — four failure modes you'll see in the field:

| What breaks | Symptom | Debug with | Fix |
|---|---|---|---|
| Endpoint URL wrong | Tool call fails, connection error | curl the endpoint directly | Fix the URL |
| stdout corrupted | Server breaks randomly | Check for print() without stderr | Add `file=sys.stderr` |
| API server down | Connection refused | curl the endpoint | Restart the API |
| Schema mismatch | Tool found, wrong args | Inspector `tools/list` | Fix function signature |

Master this table and you can troubleshoot any MCP integration in under five minutes."

**TRANSITION:** "Let's bring it home. How do you take what we just built and use it in a customer conversation?"

---

## SECTION 7 — Wrap-Up and Customer Positioning (~10 min)

### 7.1 — Practice the two-minute narrative

**SAY:**

"You now have hands-on experience with MCP. Let's convert that into something you can say to a customer. Here's the two-minute positioning narrative — practice saying this:

*'MCP is a standard interface for tool discovery and structured tool calls — like a universal port for agent integrations. Instead of building a custom connector for every system, you declare your tools once and any MCP-compatible agent can discover and use them.*

*We ground responses in retrieved sources, then generate. Every answer comes with citations you can verify. It's the difference between "the AI said so" and "here's the source document."*

*And we keep enterprise permissions intact. The agent only sees what the user is allowed to see. Every tool call goes through a defined trust boundary with structured schemas — not open-ended access to your systems.'*"

### 7.2 — Practice the one-minute technical explanation

**SAY:**

"And when the technical champion asks 'How does it actually work?' — here's your one-minute version:

*'The agent discovers available tools through MCP's schema. When a user asks a question, the agent selects the right tool, sends a structured call through JSON-RPC, and the MCP server calls the enterprise search API. Results flow back with relevance scores and citations. The agent uses those to generate a grounded answer — no hallucination, just real enterprise data.'*"

### 7.3 — The production delta conversation

**SAY:**

"You will get this question in every demo: *'Is this production-ready?'*

Here's how to answer:

*'The protocol is production-ready. For your environment, we'd add:*

- *OAuth 2.1 authorization — so the agent authenticates as the user*
- *Streamable HTTP transport — instead of stdio, so the server runs independently and supports multiple clients*
- *Origin header validation — to prevent unauthorized clients*
- *Least-privilege tool scoping — agents only see the tools they need*
- *Prompt injection controls — input validation at the tool boundary*

*Let me show you what that looks like.'*

Today we used stdio and a local endpoint to keep focus on the concepts. The code is the same — you upgrade by changing the transport and adding auth."

### 7.4 — Group discussion

**ASK THE GROUP:**

"What systems of record do your customers ask about most? Think about search, ticketing, CRM, knowledge bases. Each one of those is an MCP server tool waiting to be built."

> **Facilitator note:** Let this discussion run 2-3 minutes. Map customer systems to MCP tool surfaces. This is where lab knowledge becomes sales intuition.

### 7.5 — Confidence check

**SAY:**

"Last thing. Quick pulse check — on a scale of 1 to 5, how confident are you demoing MCP to a customer tomorrow? Raise your hand for your number."

> **Facilitator note:** Target 4+ average. If anyone is below 3, offer to pair with them after the session.

**SAY:**

"Thanks everyone. You've built an MCP server from scratch, validated grounded results, broken and fixed integrations, and practiced the customer narrative. That's the full loop — from code to customer conversation."

---
---

## POST-LAB CLEANUP

Run after the session is over:

```bash
cd ~/environment/mcp-lab
bash teardown.sh
```

This kills the mock API and any lingering server processes.

### If resetting for the next cohort

```bash
cd ~/environment/mcp-lab
bash reset-lab.sh
```

This runs teardown + setup with full validation (3 PASS tests).

### If done for the day

1. Stop the mock API: `Ctrl+C` in Terminal 1 (or `bash teardown.sh`)
2. Optionally close Cloud9

### If restarting after a break

1. Run `bash setup.sh` to re-validate
2. Start mock API: `python3.12 ~/environment/mcp-lab/mock_search_api.py`
3. Smoke test: `curl -s "http://localhost:8080/health"`

---

## APPENDIX A — Timing Guide

| Section | Topic | Target Time | Cumulative |
|---------|-------|-------------|-----------|
| 1 | Intro and customer story | 8 min | 8 min |
| 2 | Environment verification | 5 min | 13 min |
| 3 | Mock search API exploration | 15 min | 28 min |
| 4 | MCP server wiring | 15 min | 43 min |
| 5 | End-to-end validation | 15 min | 58 min |
| 6 | Troubleshooting | 12 min | 70 min |
| 7 | Wrap-up and positioning | 10 min | 80 min |

> For a **45-minute panel presentation** (interview format), compress Sections 2-3 into a quick demo (5 min), keep Section 4 (10 min), keep Section 5 (5 min), shorten Section 6 to one exercise (5 min), and keep Section 7 (5 min). Spend the remaining 15 min on Q&A.

## APPENDIX B — Emergency Fixes

| Problem | Fix |
|---------|-----|
| Mock API not responding | `python3.12 ~/environment/mcp-lab/mock_search_api.py` |
| Port 8080 already in use | `pkill -f mock_search_api; sleep 2; python3.12 ~/environment/mcp-lab/mock_search_api.py` |
| MCP Inspector hangs | `Ctrl+C`, then re-run the command |
| Python module not found | `python3.12 -m pip install --user mcp httpx` |
| Everything is broken | `bash ~/environment/mcp-lab/reset-lab.sh` |

## APPENDIX C — File Quick Reference

| File | Purpose |
|------|---------|
| `mock_search_api.py` | Mock enterprise search API (8 docs, 3 topics, local HTTP on :8080) |
| `server.py` | MCP server — `kb_search(query, top_k)` tool, stdio transport |
| `inspector-config.json` | Config for MCP Inspector CLI to find the server |
| `lambda_function.py` | Same search logic packaged for AWS Lambda (reference / production discussion) |
| `setup.sh` | Install deps + validate 3 end-to-end tests |
| `teardown.sh` | Kill all processes + clean temp files |
| `reset-lab.sh` | Teardown + setup (between cohorts) |
