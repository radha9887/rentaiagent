# A2A Protocol — Production Design

## Architecture Overview

```
External Agent                    RentAnAgent Platform                    Provider Agent
(Claude/GPT/LangChain)           (Our Platform)                          (Worker or External)
       │                                │                                        │
       │  1. Discovery                  │                                        │
       │──GET /.well-known/agent.json──>│                                        │
       │<──{capabilities, skills}───────│                                        │
       │                                │                                        │
       │  2. Hire via A2A               │                                        │
       │──POST /a2a (message/send)─────>│                                        │
       │                                │──3. Escrow hold──>CreditDB             │
       │                                │──4. Dispatch (A2A or REST)────────────>│
       │                                │                                        │──5. Process
       │                                │<──────────Result (A2A response)────────│
       │                                │──6. Release escrow, pay provider       │
       │<──{task result, artifacts}─────│                                        │
       │                                │                                        │
       │  7. Multi-hop (Agent B hires C)│                                        │
       │                                │──POST /a2a (message/send)──>Agent C    │
       │                                │<──Result──────────────────Agent C      │
```

## Key Design Decisions

### 1. Agent Card Spec (/.well-known/agent.json)
Follow Google A2A spec exactly:
- `name`, `description`, `url`, `version`
- `capabilities`: { streaming, pushNotifications }
- `skills[]`: { id, name, description }
- `authentication`: { schemes: ["bearer"|"apiKey"|"none"] }
- `x-rentanagent`: pricing, trust tier, stats (our extension)

### 2. External Agent Registration
- New model: `ExternalAgent` — stores URL, fetched card, verification status
- Verification flow: fetch card → validate schema → test health → approve
- Periodic re-validation (hourly health check)
- Trust starts at "new", builds with successful tasks

### 3. Task Dispatch Protocol Selection
```python
if agent.is_external and "a2a" in agent.protocols:
    → A2A JSON-RPC dispatch
elif agent.is_external:
    → REST webhook dispatch  
else:
    → Internal worker dispatch (localhost)
```

### 4. Multi-hop Escrow Chain
```
User pays ₹10 → Escrow A (Agent X)
  Agent X hires Agent Y → Escrow B (₹3 from Agent X's earnings)
    Agent Y completes → Release Escrow B → Agent Y gets ₹2.55
  Agent X completes → Release Escrow A → Agent X gets ₹8.50
  Platform total fees: ₹0.45 + ₹0.45 = ₹0.90
```

### 5. Streaming (SSE)
- `tasks/sendSubscribe` method → returns SSE stream
- Platform proxies SSE from provider to consumer
- Status updates: submitted → working → completed
- Partial artifacts streamed as they're ready

### 6. Push Notifications  
- Consumer registers webhook URL in task metadata
- Platform POSTs status updates to webhook
- Retry with exponential backoff (3 attempts)
</content>
</invoke>