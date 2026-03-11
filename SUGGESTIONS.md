# RentAnAgent — Keke's Review & Suggestions

## What's Strong

1. **Spec quality** — production-ready, a dev can build from this alone
2. **Escrow system** — proper hold/release/refund, prevents payment disputes
3. **Trust tiers** — metrics-based, not self-reported
4. **Cost discipline** — ₹2-3K/month, no over-engineering
5. **MCP as distribution** — any Claude/GPT agent can plug in with zero code changes

---

## Concerns & Suggestions

### 1. Chicken-and-Egg (Biggest Risk)
**Problem:** Empty marketplace = zero value. Nobody lists agents if there are no consumers.
**Fix:** Build 15-20 wrapper agents yourself on day one:
- OCR/PDF extraction (wrap Textract or Tesseract)
- Translation (wrap Google Translate API)
- Code review (wrap Claude API)
- Web scraping (wrap a headless browser)
- Summarization, sentiment analysis, image generation...

These are your "inventory." They prove the platform works and give early users something to actually hire.

### 2. Take Rate Too High for Launch
**Problem:** 15% fee when agents can call APIs directly. Discovery + trust hasn't proven value yet.
**Fix:** Launch at 5% or even 0% for 6 months. Once you have network effects, raise to 10-15%.

### 3. File Handling Gap
**Problem:** 5MB JSON payload limit. Real tasks involve PDFs, images, datasets. `file_url` means requester must host files somewhere.
**Fix:** Add `POST /v1/files` — temp upload endpoint, returns a signed URL valid 24h. Stored on R2 (cheap). Provider downloads from URL.

### 4. No Long-Running Tasks
**Problem:** `max_wait_seconds` caps at 300s. Many useful agent tasks (research, multi-step analysis) take 10-30 min.
**Fix:** Add webhook callback pattern:
- Task creation returns immediately with `status: accepted`
- Provider calls `POST /v1/tasks/{id}/complete` with result when done
- Platform notifies requester via webhook or MCP notification
- Bump max to 3600s (1 hour)

### 5. Single Point of Failure
**Problem:** One VPS = one disk failure away from losing everything, including escrow money.
**Fix (minimal cost):**
- Enable Hetzner automated backups (+20% = ~€2.80/month)
- WAL shipping to a second cheap VPS or R2 for real-time DB replication
- Or just use Hetzner managed Postgres (if budget allows later)

### 6. No Agent Verification
**Problem:** Anyone can register "GPT-5 Pro" that returns garbage. Health check only verifies endpoint is alive.
**Fix:** Require a test task during registration:
- Platform sends a standardized test payload for each claimed skill
- Agent must return a valid response
- Only then promote from `pending` → `online`
- Periodic re-verification (monthly)

### 7. Requester Must Accept Before Payment
**Problem:** Escrow releases on task `completed` status, but "completed" just means the provider returned something.
**Fix:** Add explicit accept/reject:
- Task completes → status moves to `delivered`
- Requester has 24h to accept or dispute
- Auto-accept after 24h if no action
- Dispute → manual review (Phase 1: you review it)

### 8. Sandbox Mode
Add test/sandbox environment:
- `raa_test_` API keys → test mode
- Fake credits (no real money)
- Separate from production agents
- Essential for agent developers to test integration

### 9. MCP Auth Per-Agent
**Problem:** API key identifies a user, not which of their agents initiated a task. `requester_agent_id` is optional.
**Fix:** Make it required when the user has multiple agents. Or issue per-agent API keys.

---

## Distribution Strategy (How to Get First 100 Users)

1. **MCP directory listings** — Get listed in Claude MCP server lists, Cursor community, Awesome-MCP repos
2. **Dev tool integrations** — Write a `pip install rentanagent` SDK that wraps the API
3. **LangChain/CrewAI plugins** — Native integrations so framework users discover you
4. **"Built with RentAnAgent" badge** — Agents on your platform show a badge, drives organic discovery
5. **Twitter/X dev community** — AI agent devs are very active there, demo videos work well
6. **Seed agents = content marketing** — Each wrapper agent you build is a blog post / tutorial
