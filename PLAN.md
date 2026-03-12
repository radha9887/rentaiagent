# RentAnAgent — Build Plan

## Phase 1A: Core Backend ✅ COMPLETE
- [x] Project scaffold (config, db, main, worker)
- [x] DB Models (User, APIKey, Agent, AgentSkill, Task, CreditAccount, Transaction, Escrow, Rating, AgentStats)
- [x] Alembic setup + initial migration
- [x] Pydantic schemas (request/response for all entities + cursor pagination)
- [x] Utils (hashing, JWT, pagination, custom errors)
- [x] Middleware (request ID, rate limiter stub, structured logging)
- [x] Auth endpoints (register, login, API keys, dual auth dependency)
- [x] Agent endpoints (CRUD, search with filters)
- [x] Credit endpoints (balance, topup stub, transactions)
- [x] Escrow logic (hold, release, refund — all atomic)
- [x] Task lifecycle (create, get, list, cancel, complete + routing stub)
- [x] Ratings + trust tier calculation + matching query
- [x] Admin endpoints (metrics, approve, suspend)
- [x] Health check (DB + Redis)
- [x] Router aggregation

## Phase 1B: MCP Server ✅ COMPLETE
- [x] MCP protocol helpers (JSON-RPC 2.0, MCPRequest/Response/Error)
- [x] 4 MCP tools: search_agents, post_task, check_task_status, rate_agent
- [x] SSE endpoint (GET /mcp/sse) with session management + heartbeats
- [x] Message endpoint (POST /mcp/messages) with full method dispatch
- [x] Test script (scripts/test_mcp.py)
- [x] Compatible with Claude Desktop MCP client format

## Phase 1C: A2A Protocol & Provider Integration ✅ COMPLETE
- [x] A2A protocol types (states, parts, artifacts, JSON-RPC helpers)
- [x] Platform agent card (/.well-known/agent.json)
- [x] Per-agent cards (/a2a/agents/{slug}/agent.json)
- [x] A2A JSON-RPC server (message/send, tasks/get, tasks/cancel)
- [x] A2A outbound client (a2a + https fallback, HMAC signing)
- [x] Provider routing with escrow integration (simulation mode default)
- [x] Health check periodic task (Celery beat, 5 min interval)
- [x] Config: HMAC_SECRET, HEALTH_CHECK_TIMEOUT_SECONDS, SIMULATION_MODE

## Phase 1D: Deployment ✅ COMPLETE
- [x] PostgreSQL + Redis on VPS
- [x] API on port 8100, Dashboard on port 3100
- [x] E2E tested (register → agent → task → escrow → pay → rate)

## Phase 1E: Real Agents + UI ✅ COMPLETE
- [x] 15 real agent workers (ports 8201-8215), pure Python, no LLM
- [x] Worker framework with HMAC validation (workers/base_worker.py)
- [x] Registration + runner + E2E test scripts
- [x] Simulation mode OFF — real task dispatch working
- [x] Public marketplace (/agents) with search + filters
- [x] Agent detail page (/agents/[slug]) with Quick Hire form
- [x] Task detail page (/tasks/[id]) with live polling + status timeline
- [x] Post task flow (/tasks/new) — select agent → skill → payload → cost preview
- [x] API docs page (/docs) — REST, MCP, A2A setup examples
- [x] Dashboard redesign — green terminal aesthetic throughout
- [x] Shared Navbar with auth state across all pages

## Phase 2: Production Ready
- [ ] Systemd services (API + dashboard + workers — stop process babysitting)
- [ ] Domain + nginx reverse proxy + Let's Encrypt SSL
- [ ] Razorpay integration (buy credits with real money)
- [ ] Better error messages (show "Insufficient credits" not generic errors)
- [ ] Mobile responsive
- [ ] Agent health checks (auto-offline dead agents)
- [ ] New user onboarding (free credits on signup, guided first task)

## Phase 3: A2A Protocol — Real Implementation
- [ ] External A2A agent registration (agents hosted elsewhere register via agent card URL)
- [ ] A2A discovery (fetch /.well-known/agent.json from external URLs)
- [ ] Inbound A2A: external agents POST tasks TO our platform agents
- [ ] Outbound A2A: our platform dispatches tasks via A2A JSON-RPC (not just REST webhooks)
- [ ] A2A streaming (SSE for long-running tasks)
- [ ] A2A push notifications (task status callbacks)
- [ ] Multi-hop: Agent A hires Agent B who hires Agent C (nested escrow)
- [ ] Agent card validation + trust scoring for external agents
- [ ] A2A test suite with mock external agents
- [ ] Demo: Claude/GPT agent discovers and hires a RentAnAgent provider via A2A

## Phase 4: Growth
- [ ] SDK packages (pip install rentanagent / npm install rentanagent)
- [ ] SSE streaming for task status in UI
- [ ] Webhook notifications for task completion
- [ ] Agent analytics dashboard (revenue charts, usage over time)
- [ ] Public API playground in docs
- [ ] pytest suite + CI pipeline
- [ ] Docker Compose (app + postgres + redis)

## Phase 5: Go-to-Market
- [ ] Landing page SEO + copy
- [ ] Twitter/LinkedIn launch
- [ ] 2-3 "real" agents with actual API backends (LLM summarizer, real OCR)
- [ ] Subscription billing (monthly agent hosting plans)
- [ ] Blog / tutorials
