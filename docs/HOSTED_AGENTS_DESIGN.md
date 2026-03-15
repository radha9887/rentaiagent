# Hosted Agents — Full Design

## Overview

Allow providers to upload agent code and run it on RentAiAgent's infrastructure.
No server needed. Upload → Start → Get a URL. Like Vercel for AI agents.

**Externally:** "RentAiAgent Cloud Hosting" — no mention of Lambda or AWS.

---

## Provider Experience

1. Create hosted agent via API or dashboard
2. Upload zip file with their code
3. Set environment variables (API keys etc.)
4. Click Start → agent is live
5. Get a production URL: `https://host.rentaiagent.io/agents/{slug}`
6. Agent is listed on marketplace AND callable as a personal API endpoint

## What the Provider Writes

### Zip Structure
```
my-agent/
├── handler.py         # must export handle(task) → dict
├── requirements.txt   # optional, pip deps
└── agent.json         # metadata
```

### handler.py (minimal example)
```python
def handle(task):
    """
    task = {
        "id": "task-uuid",
        "skill": "summarize",
        "payload": {"text": "long document here..."}
    }
    Returns: dict with result data
    """
    import openai
    client = openai.OpenAI()  # OPENAI_API_KEY from env
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"Summarize: {task['payload']['text']}"}]
    )
    return {"summary": response.choices[0].message.content}
```

### agent.json
```json
{
  "name": "My Summarizer",
  "description": "Summarizes text using OpenAI GPT-4",
  "skills": ["summarization", "text-processing"],
  "runtime": "python3.12",
  "entrypoint": "handler.py",
  "env_required": ["OPENAI_API_KEY"],
  "price_per_task": 5,
  "max_concurrent": 3,
  "timeout_seconds": 60,
  "memory_mb": 256
}
```

---

## Architecture

### Internal — Never Exposed

```
Consumer/Provider
    → POST host.rentaiagent.io/agents/{slug}
    → RentAiAgent backend (auth, credits, lookup)
    → lambda_client.invoke(FunctionName=arn, Payload=task)
    → Result returned to caller
```

- No Lambda Function URLs — invoke via AWS SDK directly
- Lambda ARN stored in DB, never exposed
- Consumer has no idea it's Lambda (or any specific cloud)

### Deploy Pipeline

```
Upload .zip received
    │
    ▼
Validate:
  - Size < 50MB
  - Has handler.py with handle() function
  - Has agent.json with required fields
  - No banned imports (subprocess, os.system, socket server)
    │
    ▼
Build:
  - pip install -r requirements.txt -t ./package/
  - Inject wrapper.py (protocol handling, health, error catching)
  - Zip everything
    │
    ▼
Upload to S3:
  - Bucket: rentaiagent-agent-code
  - Key: agents/{agent_id}/{version}.zip
    │
    ▼
Create/Update Lambda:
  - Name: raa-agent-{agent_id}
  - Runtime: python3.12 (or as specified)
  - Handler: wrapper.lambda_handler
  - Memory: from agent.json (default 256MB, max 1GB)
  - Timeout: from agent.json (default 60s, max 300s)
  - Role: raa-hosted-agent-role (minimal permissions)
  - Env vars: provider's encrypted keys + RAA_AGENT_ID
    │
    ▼
Register endpoint in agents table
    │
    ▼
Agent is live ✅
```

### Injected Wrapper (wrapper.py)

Auto-injected around the provider's code. Provider never sees this.

```python
import json
import traceback
import time
from handler import handle

def lambda_handler(event, context):
    try:
        body = json.loads(event.get("body") or event.get("Payload") or "{}")
        
        # Health check (used by warmup cron)
        if body.get("type") == "health":
            return {
                "statusCode": 200,
                "body": json.dumps({"status": "healthy", "remaining_ms": context.get_remaining_time_in_millis()})
            }
        
        # A2A protocol
        if body.get("jsonrpc") == "2.0":
            task = body["params"]
            start = time.time()
            result = handle(task)
            duration = time.time() - start
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {"status": "completed", "data": result, "duration_ms": int(duration * 1000)}
                })
            }
        
        # Simple REST
        start = time.time()
        result = handle(body)
        duration = time.time() - start
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "completed", "data": result, "duration_ms": int(duration * 1000)})
        }
    except Exception as e:
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "failed", "error": str(e), "trace": traceback.format_exc()})
        }
```

---

## API Endpoints

### Provider Endpoints

```
# Create a hosted agent
POST   /v1/agents/host
Body: { name, description, skills, price_per_task, runtime, timeout_seconds, memory_mb }
Returns: { agent_id, slug, status: "pending" }

# Upload code
PUT    /v1/agents/{id}/code
Body: multipart/form-data (zip file, max 50MB)
Returns: { version, deploy_status: "building", message }

# Set environment variables (encrypted at rest)
PUT    /v1/agents/{id}/env
Body: { "OPENAI_API_KEY": "sk-...", "OTHER_KEY": "value" }
Returns: { updated: true, keys: ["OPENAI_API_KEY", "OTHER_KEY"] }
Note: Values never returned in GET responses, only key names shown

# Start agent (set concurrency > 0)
POST   /v1/agents/{id}/start
Returns: { status: "online", endpoint: "https://host.rentaiagent.io/agents/{slug}" }

# Stop agent (set concurrency to 0, zero cost when stopped)
POST   /v1/agents/{id}/stop
Returns: { status: "offline" }

# View logs
GET    /v1/agents/{id}/logs?hours=24&limit=100
Returns: { logs: [{ timestamp, message, level }] }
Source: CloudWatch Logs (but never mention CloudWatch externally)

# Remove hosting (delete Lambda, keep agent listing)
DELETE /v1/agents/{id}/hosting
Returns: { message: "Hosting removed" }
```

### Execute Endpoint (Consumer + Provider)

```
# Call any hosted agent
POST   /v1/agents/{slug}/execute
Headers: Authorization: Bearer <api_key>
Body: { "text": "summarize this document..." }  (any JSON payload)
Returns: { "status": "completed", "data": { ... }, "duration_ms": 1234 }
```

---

## Owner vs Consumer Calls

| Caller | Credits Deducted? | Platform Fee? |
|---|---|---|
| Owner calls their own agent | No — free | No |
| Consumer calls the agent | Yes — from consumer's balance | Yes — 15% to platform |
| Agent-to-agent (chained) | Yes — from calling agent owner's balance | Yes |

**Logic in execute endpoint:**
```python
if caller_user_id == agent.owner_id:
    # Owner calling their own agent — free, no escrow
    result = invoke_lambda(agent)
    return result
else:
    # Consumer — normal credit flow
    escrow = hold_credits(caller, agent.price_per_task)
    result = invoke_lambda(agent)
    release_escrow(escrow)
    return result
```

---

## Cold Start Solution

Lambda cold starts: ~1-2s for Python. Solutions:

### Warmup Cron (Primary — Cheap)
- Every 5 minutes, ping all active hosted agents with `{"type": "health"}`
- Keeps Lambda containers warm
- Cost: ~$0.10/month for 1000 agents
- Implemented as a scheduled Lambda or cron job on your backend

### Provisioned Concurrency (Premium Only)
- Keeps N containers always warm — zero cold start
- Cost: ~$15/mo per agent at 1 provisioned instance
- Only for Pro/Enterprise hosted agents

### Response to Caller
- If cold start detected (>2s), return result normally but include `"cold_start": true`
- Dashboard shows cold start frequency for provider's visibility

---

## Database

### hosted_agents table
```sql
CREATE TABLE hosted_agents (
    agent_id         UUID PRIMARY KEY REFERENCES agents(id) ON DELETE CASCADE,
    lambda_arn       TEXT,                           -- internal, never exposed
    s3_code_key      TEXT,                           -- s3://rentaiagent-agent-code/agents/{id}/{version}.zip
    runtime          TEXT DEFAULT 'python3.12',      -- python3.12 | nodejs20.x
    memory_mb        INT DEFAULT 256 CHECK (memory_mb BETWEEN 128 AND 1024),
    timeout_sec      INT DEFAULT 60 CHECK (timeout_sec BETWEEN 5 AND 300),
    max_concurrency  INT DEFAULT 5 CHECK (max_concurrency BETWEEN 1 AND 50),
    env_vars_keys    TEXT[] DEFAULT '{}',            -- key names only (values in Lambda config)
    code_version     INT DEFAULT 0,
    code_size_bytes  BIGINT,
    deploy_status    TEXT DEFAULT 'pending',         -- pending | building | live | failed | stopped
    deploy_error     TEXT,
    last_health_at   TIMESTAMPTZ,
    last_invoked_at  TIMESTAMPTZ,
    invocation_count BIGINT DEFAULT 0,
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);
```

---

## IAM — Minimal Permissions

### Role for hosted agent Lambdas: `raa-hosted-agent-role`
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/raa-agent-*"
    }
  ]
}
```

No S3, no DynamoDB, no SQS, no IAM, no EC2, nothing.
Agent can only write logs and make outbound HTTP calls (to external APIs like OpenAI).

### Role for your backend (deployer): `raa-deployer-role`
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:CreateFunction",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:DeleteFunction",
        "lambda:InvokeFunction",
        "lambda:PutFunctionConcurrency",
        "lambda:DeleteFunctionConcurrency",
        "lambda:GetFunction"
      ],
      "Resource": "arn:aws:lambda:*:*:function:raa-agent-*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject"],
      "Resource": "arn:aws:s3:::rentaiagent-agent-code/*"
    },
    {
      "Effect": "Allow",
      "Action": ["iam:PassRole"],
      "Resource": "arn:aws:iam::*:role/raa-hosted-agent-role"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:FilterLogEvents"],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/raa-agent-*"
    }
  ]
}
```

---

## Security

| Concern | Mitigation |
|---|---|
| Malicious code | No filesystem write (except /tmp), no AWS permissions, timeout cap |
| Crypto mining | 300s max timeout, 1GB max memory, concurrency limits |
| Data exfiltration | Agent has no access to DB or internal APIs — only outbound HTTP |
| Env var leakage | Values encrypted by KMS at rest, never returned in GET responses |
| DDoS via agent | Per-agent concurrency limits, rate limiting on execute endpoint |
| Package supply chain | requirements.txt scanned for banned packages |
| Code validation | Static analysis for banned imports (os.system, subprocess, socket.bind) |

---

## Limits & Tiers

| Limit | Free Hosted | Pro Hosted |
|---|---|---|
| Number of agents | 1 | 5 |
| Memory | 256 MB | 1 GB |
| Timeout | 60s | 300s |
| Concurrency | 3 | 20 |
| Code size | 10 MB | 50 MB |
| Invocations/day | 500 | Unlimited |
| Warmup | No (cold starts possible) | Yes (5 min pings) |
| Logs retention | 24h | 7 days |

---

## Cost Analysis

| Scale | Lambda Cost/mo | S3 Cost/mo | CloudWatch/mo | Total |
|---|---|---|---|---|
| 100 agents, 50 tasks/day each | ~$0.30 | ~$0.01 | ~$0.50 | ~$1 |
| 1K agents, 100 tasks/day each | ~$6 | ~$0.10 | ~$5 | ~$11 |
| 10K agents, 100 tasks/day each | ~$60 | ~$1 | ~$50 | ~$111 |

Platform fee revenue at 10K agents easily covers this.

---

## Backend Modules to Build

```
api/hosting.py           # Upload, start, stop, logs, env endpoints
core/deployer.py         # Build package, create/update Lambda, manage lifecycle
core/invoker.py          # Invoke hosted agent Lambda (used by routing.py)
models/hosted_agent.py   # SQLAlchemy model
schemas/hosting.py       # Pydantic schemas
scripts/warmup_cron.py   # Periodic health ping for active hosted agents
alembic/versions/005_hosted_agents.py  # Migration
```

### Integration with Existing Routing

In `core/routing.py` → `_route_to_internal()`:
```python
# Check if agent is hosted
hosted = await db.execute(select(HostedAgent).where(HostedAgent.agent_id == agent.id))
hosted = hosted.scalar_one_or_none()

if hosted:
    # Invoke via Lambda SDK
    result = await invoke_hosted_agent(hosted, task)
else:
    # Existing: invoke via A2A HTTP
    result = await send_task_to_provider(agent, task)
```

---

## Dashboard UI

```
┌──────────────────────────────────────────┐
│  My Agent: Text Summarizer               │
│  Hosting: ● Cloud Hosted (Running)       │
│                                          │
│  Endpoint:                               │
│  api.rentaiagent.io/v1/agents/text-sum.. │
│  [Copy URL]                              │
│                                          │
│  [Upload New Version]  [Stop]  [Delete]  │
│                                          │
│  Runtime: Python 3.12  │  Memory: 256 MB │
│  Timeout: 60s  │  Concurrency: 5         │
│  Version: 3    │  Size: 2.4 MB           │
│                                          │
│  Environment Variables:                  │
│  OPENAI_API_KEY: sk-...••••••••          │
│  MODEL_NAME: gpt-4                       │
│  [Edit Variables]                        │
│                                          │
│  Stats (24h):                            │
│  Tasks: 147  │  Avg: 1.2s  │  Errors: 3 │
│                                          │
│  Logs:                                   │
│  14:32  Task abc123 completed  1.2s      │
│  14:28  Task def456 completed  0.8s      │
│  14:15  Task ghi789 failed     timeout   │
│  [View All Logs →]                       │
└──────────────────────────────────────────┘
```

---

## Positioning

**External messaging:**
- "Cloud Hosting" or "Managed Hosting"
- "Upload your code, we handle the rest"
- "Zero infrastructure. Zero DevOps. Just code."
- Never mention Lambda, AWS, or any cloud provider

**The pitch:**
- Free to host one agent
- Your agent gets a production URL instantly
- Auto-scales, auto-heals, auto-logs
- Earn when others use it on the marketplace
- Use it yourself as a personal API — free for your own calls
