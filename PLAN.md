# RentAnAgent — Build Plan

## Phase Breakdown

### Phase 1A: Core Backend (Week 1-2) ← START HERE
Get the API running locally with the full task lifecycle.

```
1. Project scaffold (FastAPI + SQLAlchemy + Alembic + Celery)
2. DB models + migrations (all tables from spec)
3. Auth system (register, login, API keys with bcrypt)
4. Agent CRUD + search (register, list, search with pg_trgm)
5. Credit system (balance, topup stub, transactions)
6. Escrow logic (hold, release, refund — all in DB transactions)
7. Task lifecycle (create → escrow → route → complete/fail → settle)
8. Rating submission + agent_stats recalculation
9. Tests for the full flow
```

**Milestone:** You can register 2 agents, post a task from one to another, see credits move.

### Phase 1B: MCP Server (Week 3)
The killer feature — what makes this discoverable.

```
1. SSE endpoint (/mcp/sse)
2. 4 tools: search_agents, post_task, check_task_status, rate_agent
3. MCP protocol handshake (initialize, tools/list, tools/call)
4. Test with Claude Desktop or claude-code
```

**Milestone:** Add RentAnAgent as MCP server in Claude, search and hire an agent from chat.

### Phase 1C: A2A + Provider Integration (Week 4)
Make it work with real external agents.

```
1. Agent Card endpoints (/.well-known/agent.json, per-agent cards)
2. A2A JSON-RPC server (receive tasks)
3. A2A client (send tasks to external agents)
4. HTTPS fallback for non-A2A agents
5. Health check system (Celery beat, 5-min intervals)
```

### Phase 1D: Payments + Deploy (Week 5)
Real money, real server.

```
1. Razorpay integration (create order, verify webhook, add credits)
2. Hetzner VPS setup (Postgres, Redis, Caddy, systemd)
3. CI/CD pipeline (GitHub Actions)
4. Cloudflare DNS + SSL
5. Backup script (pg_dump → R2)
```

### Phase 1E: Seed & Launch (Week 6)
Bootstrap the marketplace.

```
1. Build 10-15 wrapper agents (OCR, translation, summarization, etc.)
2. Register them on the platform
3. Write SDK (`pip install rentanagent`)
4. Landing page (app.rentanagent.io)
5. Submit to MCP directories + Awesome lists
6. Tweet thread / demo video
```

---

## Where to Start RIGHT NOW

**Step 1:** Scaffold the project locally.

```bash
cd ~/workspace/rentanagent
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn sqlalchemy[asyncio] asyncpg alembic redis celery pydantic pydantic-settings
```

**Step 2:** Build `config.py`, `db.py`, `main.py` — the skeleton.

**Step 3:** DB models + first migration.

**Step 4:** Auth endpoints (register + login + API keys).

That's your first day. Want me to start scaffolding?
