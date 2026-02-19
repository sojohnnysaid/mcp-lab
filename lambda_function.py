import json

# ---------------------------------------------------------------------------
# Mock Enterprise Search API  —  deterministic canned data
# 8 documents across 3 topic clusters: renewals, onboarding, security
# ---------------------------------------------------------------------------

DOCUMENTS = [
    # --- Renewals cluster ---
    {
        "doc_id": "DOC-042",
        "title": "Q4 2024 Renewal Playbook",
        "snippet": "Standard renewal process begins 90 days before contract expiration. Account team opens a renewal opportunity in Salesforce and schedules a business review with the champion.",
        "url": "https://wiki.acme.co/renewals/q4-2024",
        "score": 0.0,
        "acl_group": "sales-team",
        "keywords": ["renewal", "renew", "contract", "expiration", "q4", "playbook", "quarterly"],
    },
    {
        "doc_id": "DOC-043",
        "title": "Renewal Pricing Guidelines 2024",
        "snippet": "Uplift targets: 5-8% for standard renewals, 10-15% for expansions. Discounts beyond 12% require VP Sales approval. Multi-year commitments receive a 3% reduction per additional year.",
        "url": "https://wiki.acme.co/renewals/pricing-2024",
        "score": 0.0,
        "acl_group": "sales-team",
        "keywords": ["renewal", "pricing", "discount", "uplift", "multi-year", "contract"],
    },
    {
        "doc_id": "DOC-044",
        "title": "Churn Risk Indicators and Mitigation",
        "snippet": "Key churn signals: declining product usage below 40% of licensed seats, no executive sponsor identified, support tickets exceeding 5 per month. Mitigation requires CSM escalation within 48 hours.",
        "url": "https://wiki.acme.co/renewals/churn-risk",
        "score": 0.0,
        "acl_group": "sales-team",
        "keywords": ["churn", "risk", "renewal", "mitigation", "usage", "retention"],
    },
    # --- Onboarding cluster ---
    {
        "doc_id": "DOC-101",
        "title": "New Employee Onboarding Checklist",
        "snippet": "All new hires must complete: IT provisioning (day 1), security training (week 1), product certification (week 2), and shadow a customer call (week 3). Manager confirms completion in Workday.",
        "url": "https://wiki.acme.co/hr/onboarding-checklist",
        "score": 0.0,
        "acl_group": "all-employees",
        "keywords": ["onboarding", "new hire", "employee", "checklist", "training", "provisioning"],
    },
    {
        "doc_id": "DOC-102",
        "title": "Customer Onboarding Playbook",
        "snippet": "Post-signature onboarding follows a 30-60-90 day framework. Week 1: technical kickoff and SSO configuration. Week 2-4: data connector setup and initial crawl. Day 30: first value milestone review.",
        "url": "https://wiki.acme.co/cs/customer-onboarding",
        "score": 0.0,
        "acl_group": "customer-success",
        "keywords": ["onboarding", "customer", "implementation", "sso", "connector", "kickoff"],
    },
    {
        "doc_id": "DOC-103",
        "title": "IT Access Provisioning Policy",
        "snippet": "Access requests are submitted via ServiceNow. Standard SLA: 4 hours for basic tools (email, Slack), 24 hours for engineering systems (GitHub, AWS). Emergency access requires manager + Security team approval.",
        "url": "https://wiki.acme.co/it/access-provisioning",
        "score": 0.0,
        "acl_group": "all-employees",
        "keywords": ["onboarding", "access", "provisioning", "it", "servicenow", "tools"],
    },
    # --- Security cluster ---
    {
        "doc_id": "DOC-201",
        "title": "Data Classification and Handling Policy",
        "snippet": "Four classification levels: Public, Internal, Confidential, Restricted. Confidential data requires encryption at rest (AES-256) and in transit (TLS 1.2+). Restricted data must not leave approved storage systems.",
        "url": "https://wiki.acme.co/security/data-classification",
        "score": 0.0,
        "acl_group": "security-team",
        "keywords": ["security", "data", "classification", "encryption", "policy", "confidential", "restricted"],
    },
    {
        "doc_id": "DOC-202",
        "title": "Incident Response Runbook",
        "snippet": "Severity 1 incidents require: immediate Slack war-room (#incident-active), PagerDuty escalation to on-call SRE, customer notification within 60 minutes, and post-incident review within 48 hours.",
        "url": "https://wiki.acme.co/security/incident-response",
        "score": 0.0,
        "acl_group": "security-team",
        "keywords": ["security", "incident", "response", "runbook", "escalation", "sre", "pagerduty"],
    },
]


def _score_document(doc, query_terms):
    """Simple keyword-overlap scoring for deterministic results."""
    keywords = doc["keywords"]
    title_lower = doc["title"].lower()
    snippet_lower = doc["snippet"].lower()

    score = 0.0
    for term in query_terms:
        if term in keywords:
            score += 0.30
        if term in title_lower:
            score += 0.20
        if term in snippet_lower:
            score += 0.10

    return min(round(score, 2), 0.99)


def handler(event, context):
    """AWS Lambda handler — Function URL compatible."""
    # Support both Function URL and direct invoke formats
    params = event.get("queryStringParameters") or {}
    query = params.get("q", "")
    top_k = int(params.get("top_k", "3"))

    query_lower = query.lower()
    query_terms = [t.strip() for t in query_lower.split() if len(t.strip()) > 2]

    scored = []
    for doc in DOCUMENTS:
        s = _score_document(doc, query_terms)
        if s > 0:
            result = {k: v for k, v in doc.items() if k != "keywords"}
            result["score"] = s
            scored.append(result)

    scored.sort(key=lambda d: d["score"], reverse=True)
    results = scored[:top_k]

    body = json.dumps({"query": query, "results": results})

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": body,
    }
