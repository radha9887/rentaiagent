# RentAnAgent — Pending Tasks

## 🔴 Critical (Must-do before sharing with anyone)

### Infrastructure
- [ ] **Systemd services** — API, dashboard, and workers die randomly. Need `rentanagent-api.service`, `rentanagent-dash.service`, `rentanagent-workers.service`
- [ ] **Domain + SSL** — Currently `http://72.61.225.168:3100`. Need a domain + nginx reverse proxy + Let's Encrypt. Nobody trusts a raw IP.
- [ ] **Environment config** — API URL hardcoded as `http://72.61.225.168:8100` in frontend. Should be env-based for prod deployment.

### Security
- [ ] **Rate limiting** — No rate limits anywhere. A bot could drain credits or DDoS agents.
- [ ] **Input validation** — Payload size limits on tasks (currently unlimited JSON).
- [ ] **API key rotation** — Keys can't be rotated without revoking. Need seamless rotation.
- [ ] **CORS lockdown** — Currently `allow_origins=["*"]`. Lock to your domain in production.

### Data
- [ ] **Database backups** — Zero backup strategy. One bad migration = everything gone.
- [ ] **Log aggregation** — Logs go to /tmp files. Need proper log rotation or a logging service.

## 🟡 Important (Before public launch)

### Payments
- [ ] **Real payments** — Credits are fake. Need Stripe/Paddle/Nevermined for real money.
- [ ] **Free credits on signup** — Currently 0 credits on register (except via /developers). Auto-grant 100 credits.
- [ ] **Pricing page** — No pricing info anywhere. Users don't know what things cost.

### UX
- [ ] **Better error messages** — "Failed to create task" instead of "Insufficient credits — top up at /credits"
- [ ] **Mobile responsive** — Dashboard and public pages break on phone.
- [ ] **Loading states** — Some pages flash empty before data loads.
- [ ] **404 page** — Missing. Broken URLs show blank screen.
- [ ] **Email verification** — Anyone can register with any email. No verification.
- [ ] **Password reset** — No forgot password flow.

### Agent Quality
- [ ] **Agent testing on registration** — When someone publishes an agent, test it with a sample payload before listing.
- [ ] **Agent SLA/uptime display** — Show historical uptime %, not just current status.
- [ ] **Agent versioning** — No way to update an agent without breaking consumers.
- [ ] **Skill taxonomy** — Skills are free-text. Need standardized categories.

### Documentation
- [ ] **Quickstart tutorial** — Step-by-step "deploy your first agent in 5 minutes".
- [ ] **Agent builder guide** — How to build an agent that works with RentAnAgent.
- [ ] **Video walkthrough** — Demo video on homepage.

## 🟢 Nice to Have (Post-launch)

- [ ] SDK packages (`pip install rentanagent` / `npm install rentanagent`)
- [ ] Agent analytics dashboard (revenue charts, usage over time)
- [ ] Interactive API playground in docs
- [ ] Agent comparison tool (compare 2-3 agents side by side)
- [ ] Dispute resolution (what if agent returns garbage?)
- [ ] Agent templates (one-click deploy common agent types)
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Docker Compose for local dev
- [ ] pytest suite
- [ ] Cross-platform A2A settlement (Nevermined integration)
