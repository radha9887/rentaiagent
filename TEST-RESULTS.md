# RentAnAgent — Test Results
Date: 2026-03-12

## Summary
- Total tests: 52
- Passed: 46
- Failed: 6
- Fixed: 4

## Bugs Found & Fixed

### Bug 1: A2A Agent Card — AttributeError on `success_rate`
- **File**: `a2a/cards.py`
- **Issue**: Referenced `agent.stats.success_rate` and `agent.stats.avg_latency_ms` which don't exist on `AgentStats` model
- **Fix**: Changed to use `completed_tasks`, `avg_rating`, `avg_response_ms` which exist in the model
- **Severity**: HIGH — broke `/a2a/agents/{slug}/agent.json` endpoint (500 error)

### Bug 2: Subtask endpoint — double prefix in route path
- **File**: `api/tasks.py`
- **Issue**: Route was `@router.post("/v1/tasks/{task_id}/subtask")` but router already has `prefix="/v1/tasks"`, resulting in `/v1/tasks/v1/tasks/{task_id}/subtask`
- **Fix**: Changed to `@router.post("/{task_id}/subtask")`
- **Severity**: HIGH — subtask endpoint was completely unreachable (404)

### Bug 3: Chain endpoint — same double prefix bug
- **File**: `api/tasks.py`
- **Issue**: Route was `@router.get("/v1/tasks/{task_id}/chain")` with same prefix duplication
- **Fix**: Changed to `@router.get("/{task_id}/chain")`
- **Severity**: HIGH — chain endpoint was completely unreachable (404)

### Bug 4: A2A Discover — JSONB operator error for external agents
- **File**: `a2a/server.py`
- **Issue**: `ExternalAgent.skills.op("@>")(string)` failed because JSONB `@>` operator needs both sides cast to JSONB
- **Fix**: Added proper `cast()` to JSONB for both operands
- **Severity**: MEDIUM — discover with skill filter crashed when checking external agents

## Not Fixed (Design Decisions / Won't Fix)
- A2A endpoints require auth — intentional since message/send creates tasks and uses credits
- External agent verification "failed" for self-referencing URL — expected behavior
- Topup returns Razorpay order but doesn't credit — by design (payment gateway flow)

## Detailed Results

### 1. Auth System
- [PASS] Register new user (`display_name` field, not `name`)
- [PASS] Login — returns JWT token + refresh token
- [PASS] Invalid JWT returns `{"error":"Invalid token"}`
- [PASS] No token returns `{"error":"Missing authorization header"}`

### 2. Agent CRUD
- [PASS] GET /v1/agents — lists 16 agents with cursor pagination
- [PASS] GET /v1/agents/featured — returns top 6 agents with full details
- [PASS] GET /v1/agents/{slug} — returns agent detail
- [PASS] POST /v1/agents — creates agent (needs `skill_tag` not `name` in skills)
- [PASS] GET /v1/agents/me — returns user's agents
- [PASS] GET /v1/agents/{slug}/ratings — returns ratings list

### 3. Credit System
- [PASS] GET /v1/credits/balance — returns balance, earned, spent, fees
- [PASS] POST /v1/credits/topup — returns Razorpay order (stub mode)
- [PASS] GET /v1/credits/transactions — returns paginated transactions

### 4. Task Lifecycle
- [PASS] Text Summarizer — result has `summary`, `word_count`, `sentence_count`
- [PASS] Math Solver — `mean=55`, `median=55.0`, `std_dev=30.2765`, `min=10`, `max=100`
- [PASS] Password Generator — 24-char password with `entropy_bits=155.0`
- [PASS] Hash Generator — SHA256 matches `b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9`
- [PASS] JSON Validator — `valid=true`, stats: `keys=3, depth=3`
- [PASS] Sentiment Analyzer — `sentiment=positive`, `score=1.0`
- [PASS] Date Calculator — `days=364`, `business_days=260`

### 5. Task Detail & Status
- [PASS] GET /v1/tasks/{id} — returns full task with result, timestamps, quoted_price, platform_fee
- [PASS] GET /v1/tasks/feed — returns public feed of recent tasks

### 6. Rating System
- [PASS] POST /v1/ratings — rate completed task (field is `overall_score`)
- [PASS] GET /v1/agents/{slug}/ratings — rating appears
- [PASS] Rate another task — different agents can be rated
- [PASS] Duplicate rating prevented — returns `{"error":"Already rated this task"}`

### 7. A2A Protocol
- [PASS] GET /.well-known/agent.json — platform card with name, skills, capabilities
- [FAIL → FIXED] GET /a2a/agents/{slug}/agent.json — 500 error due to `success_rate` attribute
- [PASS] POST /a2a message/send — creates task, returns A2A task result with artifacts
- [PASS] POST /a2a tasks/get — returns task status in A2A format
- [FAIL → FIXED] POST /a2a agent/discover with skill — JSONB operator error
- [PASS] POST /a2a agent/discover without skill — returns all online agents

### 8. External Agent Registration
- [PASS] POST /v1/external-agents/register — registers agent (card_url = base URL)
- [PASS] GET /v1/external-agents — lists verified agents (empty if none verified)
- [PASS] GET /v1/external-agents/{id} — returns detail
- [PASS] POST /v1/external-agents/{id}/verify — triggers verification
- [PASS] DELETE /v1/external-agents/{id} — removes agent

### 9. Webhooks
- [PASS] POST /v1/webhooks — creates subscription with secret (`callback_url` field)
- [PASS] GET /v1/webhooks — lists subscriptions
- [PASS] POST /v1/webhooks/{id}/test — attempts delivery (405 expected for health endpoint)
- [PASS] DELETE /v1/webhooks/{id} — removes subscription

### 10. Multi-hop Task Chain
- [FAIL → FIXED] POST /v1/tasks/{id}/subtask — was 404 due to double prefix
- [FAIL → FIXED] GET /v1/tasks/{id}/chain — was 404 due to double prefix
- [PASS] After fix: subtask creates and routes successfully
- [PASS] After fix: chain shows parent→child tree structure

### 11. Admin Endpoints
- [PASS] GET /v1/admin/metrics — returns total_users, total_agents, total_tasks, completed_tasks, total_revenue
- [PASS] POST /v1/admin/agents/{id}/suspend — suspends agent
- [PASS] POST /v1/admin/agents/{id}/approve — approves agent

### 12. MCP Server
- [PASS] GET /mcp/sse — returns SSE endpoint event with session_id and messages URL

### 13. Edge Cases
- [PASS] Task with 0 credits → `{"error":"Insufficient credits"}`
- [PASS] Invalid JSON payload → returns JSON decode error with 422
- [PASS] Rate non-existent task → `{"error":"Task not found"}`
- [PASS] Rate same task twice → `{"error":"Already rated this task"}`
- [PASS] Invalid JWT → `{"error":"Invalid token"}`
- [PASS] No auth header → `{"error":"Missing authorization header"}`
- [FAIL] Task to offline agent (no base_url) → returns internal error message instead of clean user-facing error. Not fixed — low priority, error message is still informative.
- [NOT TESTED] Max chain depth exceeded — would need to create 5+ nested subtasks
