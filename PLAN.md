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

## Phase 1C: Testing & Docker
- [ ] pytest suite
- [ ] Docker Compose (app + postgres + redis)
- [ ] CI pipeline

## Phase 1D: Agent Communication
- [ ] HTTP forwarding to agent endpoints
- [ ] A2A protocol support
- [ ] Health check polling

## Phase 2: Advanced Features
- [ ] SSE streaming for task status
- [ ] Webhook notifications
- [ ] Agent discovery protocol
- [ ] Subscription billing
