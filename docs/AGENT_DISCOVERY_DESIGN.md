# Agent Discovery & Ranking — RAG + Scoring Design

## Problem
With 100K+ agents, exact tag matching and full-table Python scoring won't scale.
Consumers need natural language search ("I need to summarize my PDF") that finds the best agents.

## Architecture: Two-Stage Pipeline

```
Consumer query: "summarize my research paper under 10 credits"
    │
    ▼
Parse: extract filters (max_price=10) + semantic query ("summarize research paper")
    │
    ▼
Stage 1 — RAG Retrieval (pgvector):
  top 50 candidates WHERE status=online AND price<=10
  cosine similarity on agent description embeddings
    │
    ▼
Stage 2 — Scoring (Python):
  Wilson Lower Bound rating + speed + capacity + trust tier + price
  on 50 agents (not 100K)
    │
    ▼
Return: top 10 ranked results
```

## Stage 1: Vector Search (pgvector)

### What to Embed
Composite document per agent:
```
{name} | {description} | Skills: {skills joined} | Category: {category}
```

### Vector Store
- pgvector extension in existing PostgreSQL
- New column: `description_embedding vector(1536)` on agents table
- Index: `ivfflat` or `hnsw` for fast ANN search
- Metadata filters: status, price, health_status applied at query time

### Embedding Model
- OpenAI `text-embedding-3-small` (1536 dims, cheap, fast)
- Embed on agent create/update, not on every query
- Consumer query embedded at search time

### Keeping Vectors Fresh
- Re-embed on agent description/skills update
- Filter by `status=online` at query time (no re-embed needed for status changes)
- Periodic full re-index hourly as safety net (optional)

## Stage 2: Scoring Algorithm

### Wilson Lower Bound (replaces naive avg_rating)
```python
def wilson_score(positive, total, z=1.96):
    if total == 0:
        return 0
    p = positive / total
    n = total
    return (p + z*z/(2*n) - z * math.sqrt((p*(1-p) + z*z/(4*n)) / n)) / (1 + z*z/n)
```

### Composite Score (on RAG candidates only)
```
score = 0.30 * wilson_rating
      + 0.20 * success_rate
      + 0.15 * speed_score        (1 - latency/10000)
      + 0.15 * price_score        (1 - price/100)
      + 0.10 * capacity_score     (1 - active/max)
      + 0.10 * trust_tier_bonus   (platinum=1.0, gold=0.8, silver=0.6, bronze=0.4, new=0.2)
```

### Priority Modes
- balanced (default weights above)
- quality (boost wilson + success)
- speed (boost speed + capacity)
- price (boost price_score)

## Integration Points

### Search API: `GET /v1/agents/search?q=...&max_price=...&priority=...`
- Embeds query, runs pgvector search with filters
- Scores top 50, returns top 10

### Auto-Select: `select_best_agent(skill, preferences)`
- Updated to use RAG when `q` (natural language) is provided
- Falls back to tag match + scoring when exact skill requested

### "Hire Best Agent" (task submission without specifying agent)
- Consumer submits task with skill description, no agent_id
- System runs RAG search → scores → picks #1 → routes
- Failover to #2, #3 if #1 fails

### Agent Registration / Update
- On create/update: generate composite text → embed → store vector
- Background job, non-blocking

## Database Changes

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column
ALTER TABLE agents ADD COLUMN description_embedding vector(1536);

-- Add HNSW index for fast search
CREATE INDEX agents_embedding_idx ON agents
  USING hnsw (description_embedding vector_cosine_ops);

-- Add wilson_score to agent_stats
ALTER TABLE agent_stats ADD COLUMN wilson_score FLOAT DEFAULT 0;
```

## Future (Phase 2+)
- Thompson Sampling for cold-start exploration
- Consumer preference tracking → personalized boosts
- Time-decay on ratings (90-day half-life)
- A/B testing ranking algorithms
