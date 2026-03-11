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

## Phase 1B: Testing & Docker
- [ ] pytest suite
- [ ] Docker Compose (app + postgres + redis)
- [ ] CI pipeline

## Phase 1C: Agent Communication
- [ ] HTTP forwarding to agent endpoints
- [ ] MCP protocol support
- [ ] A2A protocol support
- [ ] Health check polling

## Phase 2: Advanced Features
- [ ] SSE streaming for task status
- [ ] Webhook notifications
- [ ] Agent discovery protocol
- [ ] Subscription billing
