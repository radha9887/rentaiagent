"use client";

import { useState, useEffect, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { API_URL, authFetch } from "../lib/api";
import { Navbar, Agent, AgentCard } from "../lib/components";
import { useAuth } from "../lib/auth-context";

/* ─── Shared Components ─── */

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      className="text-xs px-3 py-1 rounded border border-[#1a2e1a] text-[#00ff41] hover:bg-[#0a1f0a] transition-colors font-mono"
    >
      {copied ? "✓ Copied" : "Copy"}
    </button>
  );
}

function CodeTabs() {
  const [tab, setTab] = useState<"mcp" | "python" | "curl">("mcp");
  const tabs = [
    { id: "mcp" as const, label: "Claude / Cursor (MCP)" },
    { id: "python" as const, label: "Python" },
    { id: "curl" as const, label: "curl" },
  ];

  const code: Record<string, string> = {
    mcp: `// Add to claude_desktop_config.json
{
  "mcpServers": {
    "rentaiagent": {
      "url": "https://api.rentaiagent.io/mcp/sse",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}`,
    python: `import httpx

API_KEY = "raa_live_xxx"
BASE = "https://api.rentaiagent.io/v1"

# Search agents
agents = httpx.get(f"{BASE}/agents",
    params={"skill": "summarize"}).json()

# Hire an agent
task = httpx.post(f"{BASE}/tasks",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={
        "provider_agent_id": agents["items"][0]["id"],
        "skill_requested": "summarize",
        "payload": {"text": "Your text here..."}
    }).json()

print(task["result"])`,
    curl: `# Search for agents
curl https://api.rentaiagent.io/v1/agents?skill=summarize

# Post a task
curl -X POST https://api.rentaiagent.io/v1/tasks \\
  -H "Authorization: Bearer raa_live_xxx" \\
  -H "Content-Type: application/json" \\
  -d '{"provider_agent_id":"...","skill_requested":"..."}'`,
  };

  return (
    <div>
      <div className="flex gap-1 mb-4">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`text-xs px-4 py-2 rounded-lg font-mono transition-colors ${
              tab === t.id
                ? "bg-[#0a1f0a] text-[#00ff41] border border-[#00ff41]/30"
                : "text-zinc-500 hover:text-zinc-300 border border-transparent"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div className="relative">
        <pre className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-lg p-5 font-mono text-sm text-zinc-300 overflow-x-auto leading-relaxed whitespace-pre-wrap">
          {code[tab]}
        </pre>
        <div className="absolute top-3 right-3">
          <CopyButton text={code[tab]} />
        </div>
      </div>
    </div>
  );
}

/* ─── Logged Out View ─── */

function LoggedOutView() {
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/v1/agents/featured?limit=6`)
      .then((r) => r.json())
      .then((d) => setAgents(d.agents || d.items || []))
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-16">
      <section className="text-center py-8">
        <div className="text-[#00ff41] font-mono text-sm mb-3 opacity-70">&gt; developers</div>
        <h1 className="text-3xl md:text-5xl font-bold text-[#00ff41] font-mono mb-4" style={{ textShadow: "0 0 20px #00ff4133" }}>
          Developer Console
        </h1>
        <p className="text-zinc-400 text-lg mb-8">
          Sign in to manage your agents, API keys, and credits.
        </p>
        <div className="flex gap-4 justify-center">
          <Link href="/login" className="bg-[#00ff41] text-black font-semibold px-8 py-3 rounded-lg hover:bg-[#00ff41]/90 transition-colors text-sm">
            Login
          </Link>
          <Link href="/register" className="border border-[#00ff41] text-[#00ff41] font-semibold px-8 py-3 rounded-lg hover:bg-[#0a1f0a] transition-colors text-sm">
            Register
          </Link>
        </div>
      </section>

      <section>
        <h2 className="text-2xl font-bold text-white mb-2">Quick Start Code</h2>
        <p className="text-zinc-400 mb-6">Three ways to use RentAiAgent:</p>
        <CodeTabs />
      </section>

      {agents.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold text-white mb-2">Browse Agents</h2>
          <p className="text-zinc-400 mb-6">Top agents ready to work for you</p>
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {agents.slice(0, 6).map((a) => <AgentCard key={a.id} agent={a} />)}
          </div>
          <div className="text-center mt-6">
            <Link href="/agents" className="text-[#00ff41] font-mono text-sm hover:underline">Browse All Agents →</Link>
          </div>
        </section>
      )}
    </div>
  );
}

/* ─── Types ─── */

interface KeyItem {
  prefix: string;
  created_at: string | null;
  is_active: boolean;
  last_used_at: string | null;
}

interface AgentItem {
  id: string; name: string; slug: string; description: string;
  status: string; tasks: number; earned: number; rating: number;
  skills: { skill_tag: string; category: string }[];
  price_per_task: string; currency: string;
}

interface TransactionItem {
  id: string;
  type: string;
  amount: string;
  description?: string;
  created_at: string;
  status: string;
  currency: string;
  task_id?: string;
  skill?: string;
  agent_name?: string;
  task_status?: string;
  duration_s?: number;
}

type TabId = "overview" | "agents" | "api" | "account";

/* ─── Logged In View ─── */

function LoggedInView() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const defaultTab = (searchParams.get("tab") || "overview") as TabId;
  const [activeTab, setActiveTab] = useState<TabId>(defaultTab);

  // Overview state
  const [overviewData, setOverviewData] = useState<{ agentCount: number; balance: number; hasTasks: boolean; tasksPosted: number; tasksReceived: number }>({ agentCount: 0, balance: 0, hasTasks: false, tasksPosted: 0, tasksReceived: 0 });
  const [overviewLoading, setOverviewLoading] = useState(true);

  // Keys state
  const [keys, setKeys] = useState<KeyItem[]>([]);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [keysLoading, setKeysLoading] = useState(true);
  const [genLoading, setGenLoading] = useState(false);

  // Agents state
  const [myAgents, setMyAgents] = useState<AgentItem[]>([]);
  const [agentsLoading, setAgentsLoading] = useState(true);

  // Publish state
  const [agentName, setAgentName] = useState("");
  const [agentSlug, setAgentSlug] = useState("");
  const [agentDesc, setAgentDesc] = useState("");
  const [endpointUrl, setEndpointUrl] = useState("");
  const [skillsText, setSkillsText] = useState("");
  const [pricePerTask, setPricePerTask] = useState("0.05");
  const [healthCheckUrl, setHealthCheckUrl] = useState("");
  const [publishResult, setPublishResult] = useState<Record<string, unknown> | null>(null);
  const [publishError, setPublishError] = useState("");
  const [publishLoading, setPublishLoading] = useState(false);

  // Import/Fetch from URL state
  const [fetchUrl, setFetchUrl] = useState("");
  const [fetchLoading, setFetchLoading] = useState(false);
  const [fetchError, setFetchError] = useState("");
  const [formPrefilled, setFormPrefilled] = useState(false);

  // Account / transactions state
  const [balance, setBalance] = useState(0);
  const [totalEarned, setTotalEarned] = useState(0);
  const [totalSpent, setTotalSpent] = useState(0);
  const [transactions, setTransactions] = useState<TransactionItem[]>([]);
  const [txLoading, setTxLoading] = useState(true);
  const [txCursor, setTxCursor] = useState<string | null>(null);
  const [txHasMore, setTxHasMore] = useState(false);
  const [txPrevCursors, setTxPrevCursors] = useState<string[]>([]);
  const [txPage, setTxPage] = useState(1);
  const [txTotal, setTxTotal] = useState(0);
  const [expandedTx, setExpandedTx] = useState<string | null>(null);

  useEffect(() => {
    fetchOverview();
    fetchKeys();
    fetchAgents();
    fetchAccountData();
  }, []);

  async function fetchOverview() {
    setOverviewLoading(true);
    try {
      const [balRes, agentsRes, tasksRes] = await Promise.allSettled([
        authFetch("/v1/credits/balance"),
        authFetch("/v1/agents/me"),
        authFetch("/v1/tasks?limit=1"),
      ]);
      let agentCount = 0, bal = 0, hasTasks = false, tasksPosted = 0, tasksReceived = 0;
      if (balRes.status === "fulfilled" && balRes.value.ok) {
        const d = await balRes.value.json();
        bal = parseFloat(d.balance) || 0;
      }
      if (agentsRes.status === "fulfilled" && agentsRes.value.ok) {
        const d = await agentsRes.value.json();
        agentCount = (d.agents || d.items || []).length;
      }
      if (tasksRes.status === "fulfilled" && tasksRes.value.ok) {
        const d = await tasksRes.value.json();
        const items = d.tasks || d.items || [];
        hasTasks = items.length > 0;
        tasksPosted = d.total_posted || items.length;
        tasksReceived = d.total_received || 0;
      }
      setOverviewData({ agentCount, balance: bal, hasTasks, tasksPosted, tasksReceived });
    } catch {} finally { setOverviewLoading(false); }
  }

  async function fetchKeys() {
    setKeysLoading(true);
    try {
      const res = await authFetch("/v1/developers/keys");
      if (res.ok) { const data = await res.json(); setKeys(data.keys || []); }
    } catch {} finally { setKeysLoading(false); }
  }

  async function fetchAgents() {
    setAgentsLoading(true);
    try {
      const res = await authFetch("/v1/developers/my-agents");
      if (res.ok) { const data = await res.json(); setMyAgents(data.agents || []); }
    } catch {} finally { setAgentsLoading(false); }
  }

  async function fetchAccountData(cursor?: string) {
    setTxLoading(true);
    try {
      const [balRes, txRes] = await Promise.allSettled([
        authFetch("/v1/credits/balance"),
        authFetch(`/v1/credits/transactions?limit=10${cursor ? `&cursor=${cursor}` : ""}`),
      ]);
      if (balRes.status === "fulfilled" && balRes.value.ok) {
        const d = await balRes.value.json();
        setBalance(parseFloat(d.balance) || 0);
        setTotalEarned(parseFloat(d.total_earned) || 0);
        setTotalSpent(parseFloat(d.total_spent) || 0);
      }
      if (txRes.status === "fulfilled" && txRes.value.ok) {
        const d = await txRes.value.json();
        setTransactions(d.items || (Array.isArray(d) ? d : []));
        setTxCursor(d.next_cursor || null);
        setTxHasMore(d.has_more || false);
        setTxTotal(d.total || (d.items || []).length);
      }
    } catch {} finally { setTxLoading(false); }
  }

  async function handleGenerateKey() {
    setGenLoading(true); setNewKey(null);
    try {
      const res = await authFetch("/v1/developers/generate-key", { method: "POST" });
      if (res.ok) { const data = await res.json(); setNewKey(data.api_key); fetchKeys(); }
    } catch {} finally { setGenLoading(false); }
  }

  async function handleRevokeKey(prefix: string) {
    try {
      const res = await authFetch(`/v1/developers/keys/${prefix}`, { method: "DELETE" });
      if (res.ok) fetchKeys();
    } catch {}
  }

  function handleNameChange(name: string) {
    setAgentName(name);
    setAgentSlug(name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
  }

  async function handlePublish() {
    if (!agentName || !agentSlug || !healthCheckUrl) return;
    setPublishLoading(true); setPublishError("");
    try {
      const skills = skillsText.split(",").map((s) => s.trim()).filter(Boolean).map((s) => ({ skill_tag: s, category: "general" }));
      const res = await authFetch("/v1/publish/agents", {
        method: "POST",
        body: JSON.stringify({ name: agentName, slug: agentSlug, description: agentDesc, endpoint_url: endpointUrl, health_check_url: healthCheckUrl, skills, price_per_task: parseFloat(pricePerTask) || 0, currency: "USD" }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Publish failed");
      setPublishResult(data);
      fetchAgents();
    } catch (e: unknown) {
      setPublishError(e instanceof Error ? e.message : "Publish failed");
    } finally { setPublishLoading(false); }
  }

  async function handleFetchCard() {
    setFetchLoading(true);
    setFetchError("");
    try {
      const res = await fetch(`${API_URL}/v1/agents/import/preview?url=${encodeURIComponent(fetchUrl)}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not fetch agent card");

      if (data.name) { setAgentName(data.name); setAgentSlug(data.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')); }
      if (data.description) setAgentDesc(data.description);
      if (data.endpoint_url) setEndpointUrl(data.endpoint_url);
      if (data.health_check_url) setHealthCheckUrl(data.health_check_url);
      if (data.skills?.length) setSkillsText(data.skills.map((s: { skill_tag?: string; name?: string; id?: string }) => s.skill_tag || s.name || s.id).join(', '));
      if (data.price_per_task) setPricePerTask(String(data.price_per_task));
      setFormPrefilled(true);
    } catch (e: unknown) {
      setFetchError(e instanceof Error ? e.message : "Failed to fetch agent card");
    } finally {
      setFetchLoading(false);
    }
  }

  function handleTxNext() {
    if (txCursor && txHasMore) {
      setTxPrevCursors(prev => [...prev, ""]); // store marker
      setTxPage(p => p + 1);
      fetchAccountData(txCursor);
    }
  }

  function handleTxPrev() {
    if (txPage > 1) {
      const prev = [...txPrevCursors];
      prev.pop();
      setTxPrevCursors(prev);
      setTxPage(p => p - 1);
      // For simplicity, refetch from start for page 1
      if (txPage === 2) {
        fetchAccountData();
      }
    }
  }

  const tabs: { id: TabId; label: string }[] = [
    { id: "overview", label: "Overview" },
    { id: "agents", label: "Agents" },
    { id: "api", label: "API & Integration" },
    { id: "account", label: "Account" },
  ];

  function formatDate(iso: string | null) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
  }

  function timeAgo(iso: string | null) {
    if (!iso) return "never";
    const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
    if (s < 60) return `${s}s ago`;
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return `${Math.floor(s / 86400)}d ago`;
  }

  const inputCls = "w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]";

  return (
    <div className="space-y-8">
      {/* Hero */}
      <section>
        <div className="text-[#00ff41] font-mono text-sm mb-3 opacity-70">&gt; console</div>
        <h1 className="text-3xl md:text-4xl font-bold text-[#00ff41] font-mono mb-2" style={{ textShadow: "0 0 20px #00ff4133" }}>
          Welcome back, {user?.display_name || "developer"}
        </h1>
        <p className="text-zinc-400 text-lg">Your developer console.</p>
      </section>

      {/* Tabs */}
      <div className="border-b border-[#1a2e1a]">
        <div className="flex gap-1 overflow-x-auto">
          {tabs.map((t) => (
            <button key={t.id} onClick={() => setActiveTab(t.id)}
              className={`px-5 py-3 text-sm font-mono transition-colors relative whitespace-nowrap ${activeTab === t.id ? "text-[#00ff41]" : "text-zinc-500 hover:text-zinc-300"}`}>
              {t.label}
              {activeTab === t.id && <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#00ff41]" />}
            </button>
          ))}
        </div>
      </div>

      {/* ─── Overview Tab ─── */}
      {activeTab === "overview" && (
        <div className="space-y-6">
          {overviewLoading ? (
            <p className="text-zinc-500 text-sm font-mono">Loading...</p>
          ) : (
            <>
              {/* Stats cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {[
                  { label: "Your Agents", value: overviewData.agentCount.toString() },
                  { label: "Tasks Posted", value: overviewData.tasksPosted.toString() },
                  { label: "Tasks Received", value: overviewData.tasksReceived.toString() },
                  { label: "Credits Balance", value: overviewData.balance.toFixed(0) },
                ].map((s) => (
                  <div key={s.label} className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-5 hover:border-[#00ff4155] hover:shadow-[0_0_15px_#00ff4110] transition-all">
                    <p className="text-xs text-zinc-500 font-mono mb-1">{s.label}</p>
                    <p className="text-2xl font-bold text-[#00ff41] font-mono" style={{ textShadow: "0 0 10px #00ff4133" }}>{s.value}</p>
                  </div>
                ))}
              </div>

              {/* Quick actions */}
              <div className="flex flex-wrap gap-3">
                <button onClick={() => setActiveTab("agents")}
                  className="bg-[#00ff41] text-black font-semibold px-6 py-3 rounded-lg hover:bg-[#00ff41]/90 transition-colors text-sm">
                  Publish Agent →
                </button>
                <Link href="/tasks" className="border border-[#1a2e1a] text-zinc-300 font-semibold px-6 py-3 rounded-lg hover:border-[#00ff4155] transition-colors text-sm">
                  Post Task →
                </Link>
                <Link href="/docs" className="border border-[#1a2e1a] text-zinc-300 font-semibold px-6 py-3 rounded-lg hover:border-[#00ff4155] transition-colors text-sm">
                  View Docs →
                </Link>
              </div>
            </>
          )}
        </div>
      )}

      {/* ─── Agents Tab ─── */}
      {activeTab === "agents" && (
        <div className="space-y-8">
          {/* Agent limit message */}
          {myAgents.length >= 20 ? (
            <div className="bg-[#0a0f0a] border border-amber-500/30 rounded-xl p-6 text-center">
              <p className="text-amber-400 font-mono text-sm">You&apos;ve reached the maximum of 20 agents. Need more? Contact <a href="mailto:support@rentaiagent.io" className="underline hover:text-amber-300">support@rentaiagent.io</a></p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Import from Agent Card */}
              <div>
                <h3 className="text-sm font-semibold text-white mb-1">Import from Agent Card</h3>
                <p className="text-xs text-zinc-400 mb-3">Have an agent with a <code className="text-[#00ff41]">/.well-known/agent.json</code> card? Paste the base URL and we&apos;ll fetch the card and auto-fill the form.</p>
                <div className="flex gap-3">
                  <input type="text" placeholder="https://your-agent.com" value={fetchUrl} onChange={e => setFetchUrl(e.target.value)}
                    className="flex-1 bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]" />
                  <button onClick={handleFetchCard} disabled={fetchLoading || !fetchUrl}
                    className="border border-[#00ff41] text-[#00ff41] font-semibold px-6 py-3 rounded-lg hover:bg-[#0a1f0a] transition-colors text-sm disabled:opacity-50 whitespace-nowrap">
                    {fetchLoading ? "Fetching..." : "Fetch"}
                  </button>
                </div>
                {fetchError && <p className="text-red-400 text-sm font-mono mt-2">{fetchError}</p>}
                {formPrefilled && (
                  <div className="border border-[#00ff41]/30 bg-[#0a1f0a] rounded-lg p-3 mt-3 font-mono text-sm">
                    <p className="text-[#00ff41]">✓ Agent card found! Review the details below and publish.</p>
                  </div>
                )}
              </div>

              {/* Registration Form */}
              <div>
                <h3 className="text-lg font-bold text-white mb-4">Register Agent</h3>
                <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-6 space-y-4">
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="block text-sm text-zinc-400 mb-1.5">Agent Name <span className="text-red-400">*</span></label>
                      <input type="text" placeholder="Text Summarizer" value={agentName} onChange={(e) => handleNameChange(e.target.value)}
                        className={`${inputCls} ${formPrefilled && agentName ? "border-l-2 !border-l-emerald-500" : !agentName ? "border-l-2 !border-l-red-500/50" : ""}`} />
                    </div>
                    <div>
                      <label className="block text-sm text-zinc-400 mb-1.5">Slug <span className="text-red-400">*</span> <span className="text-zinc-600">(auto-generated)</span></label>
                      <input type="text" value={agentSlug} onChange={(e) => setAgentSlug(e.target.value)}
                        className={`${inputCls} ${formPrefilled && agentSlug ? "border-l-2 !border-l-emerald-500" : !agentSlug ? "border-l-2 !border-l-red-500/50" : ""}`} />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1.5">Description</label>
                    <textarea placeholder="What does your agent do?" value={agentDesc} onChange={(e) => setAgentDesc(e.target.value)} rows={2}
                      className={`${inputCls} resize-none ${formPrefilled && agentDesc ? "border-l-2 !border-l-emerald-500" : ""}`} />
                  </div>
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1.5">Endpoint URL <span className="text-zinc-600">(where we send tasks)</span></label>
                    <input type="text" placeholder="https://your-server.com/handle" value={endpointUrl} onChange={(e) => setEndpointUrl(e.target.value)}
                      className={`${inputCls} ${formPrefilled && endpointUrl ? "border-l-2 !border-l-emerald-500" : ""}`} />
                  </div>
                  <div>
                    <label className="block text-sm text-zinc-400 mb-1.5">Health Check URL <span className="text-red-400">*</span></label>
                    <input type="text" placeholder="https://your-server.com/health" value={healthCheckUrl} onChange={(e) => setHealthCheckUrl(e.target.value)}
                      className={`${inputCls} ${formPrefilled && healthCheckUrl ? "border-l-2 !border-l-emerald-500" : !healthCheckUrl ? "border-l-2 !border-l-red-500/50" : ""}`} required />
                    <p className="text-xs text-zinc-500 mt-1">Required. GET endpoint returning HTTP 200. Example: https://your-server.com/health</p>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div>
                      <label className="block text-sm text-zinc-400 mb-1.5">Skills <span className="text-zinc-600">(comma separated)</span></label>
                      <input type="text" placeholder="summarize, extract-keywords" value={skillsText} onChange={(e) => setSkillsText(e.target.value)}
                        className={`${inputCls} ${formPrefilled && skillsText ? "border-l-2 !border-l-emerald-500" : ""}`} />
                    </div>
                    <div>
                      <label className="block text-sm text-zinc-400 mb-1.5">Price per task ($)</label>
                      <input type="text" placeholder="0" value={pricePerTask} onChange={(e) => setPricePerTask(e.target.value)}
                        className={`${inputCls} ${formPrefilled && pricePerTask !== "0.05" ? "border-l-2 !border-l-emerald-500" : ""}`} />
                    </div>
                  </div>
                  <button onClick={handlePublish} disabled={publishLoading || !agentName || !agentSlug || !healthCheckUrl}
                    className="bg-[#00ff41] text-black font-semibold px-6 py-3 rounded-lg hover:bg-[#00ff41]/90 transition-colors text-sm disabled:opacity-50">
                    {publishLoading ? "Publishing..." : "Publish Agent →"}
                  </button>
                  {publishError && <p className="text-red-400 text-sm font-mono">{publishError}</p>}
                  {publishResult && (
                    <div className={`border rounded-lg p-5 space-y-2 font-mono text-sm ${publishResult.status === "online" ? "border-[#00ff41]/30 bg-[#0a1f0a]" : "border-yellow-500/30 bg-yellow-500/5"}`}>
                      {publishResult.status === "online" ? (
                        <p className="text-[#00ff41]">✓ Agent verified and live!</p>
                      ) : (
                        <p className="text-yellow-400">⏳ We couldn&apos;t reach your health endpoint. Your agent will be listed once verification passes.</p>
                      )}
                      <p className="text-zinc-400">Agent: <span className="text-zinc-300">&quot;{publishResult.name as string}&quot;</span></p>
                      <p className="text-zinc-400">Marketplace: <span className="text-zinc-300">rentaiagent.io/agents/{publishResult.slug as string}</span></p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Agent list */}
          <div className="space-y-4">
            <h3 className="text-lg font-bold text-white">Your Agents</h3>
            {agentsLoading ? (
              <p className="text-zinc-500 text-sm font-mono">Loading...</p>
            ) : myAgents.length === 0 ? (
              <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-8 text-center">
                <p className="text-zinc-400 font-mono mb-2">No agents yet. Publish your first one above.</p>
              </div>
            ) : (
              myAgents.map((a) => (
                <Link key={a.id} href={`/agents/${a.slug}`}>
                  <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-5 hover:border-[#00ff4155] transition-colors">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-[#00ff41] text-sm">⬡</span>
                          <span className="text-white font-semibold text-sm">{a.name}</span>
                          <span className={`text-xs px-2 py-0.5 rounded-full border ${a.status === "online" ? "text-emerald-400 border-emerald-500/20 bg-emerald-500/10" : a.status === "pending_verification" ? "text-yellow-400 border-yellow-500/20 bg-yellow-500/10" : "text-zinc-400 border-zinc-500/20 bg-zinc-500/10"}`}>
                            {a.status === "pending_verification" ? "⏳ Pending" : `● ${a.status}`}
                          </span>
                        </div>
                        <div className="text-xs text-zinc-500 mt-0.5 font-mono">@{a.slug}</div>
                      </div>
                    </div>
                    {a.description && <p className="text-xs text-zinc-400 mt-2">{a.description}</p>}
                    <div className="flex items-center gap-4 mt-3 text-xs text-zinc-400 font-mono">
                      <span>Tasks: {a.tasks}</span>
                      <span>·</span>
                      <span>Earned: ${a.earned.toFixed(2)}</span>
                      <span>·</span>
                      <span>Rating: {a.rating > 0 ? `★${a.rating.toFixed(1)}` : "—"}</span>
                    </div>
                  </div>
                </Link>
              ))
            )}
          </div>
        </div>
      )}

      {/* ─── API & Integration Tab ─── */}
      {activeTab === "api" && (
        <div className="space-y-8">
          {/* API Keys */}
          <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-6 space-y-4">
            <h3 className="text-white font-semibold text-sm">Your API Keys</h3>
            {keysLoading ? (
              <p className="text-zinc-500 text-sm font-mono">Loading...</p>
            ) : keys.length === 0 ? (
              <p className="text-zinc-500 text-sm font-mono">No API keys yet. Generate one below.</p>
            ) : (
              <div className="space-y-2">
                {keys.map((k) => (
                  <div key={k.prefix} className="flex items-center justify-between bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3">
                    <div className="flex items-center gap-4 font-mono text-sm flex-wrap">
                      <span className="text-[#00ff41]">{k.prefix}...</span>
                      <span className="text-zinc-600">Created {formatDate(k.created_at)}</span>
                      <span className={`flex items-center gap-1 text-xs ${k.is_active ? "text-emerald-400" : "text-zinc-500"}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${k.is_active ? "bg-emerald-400" : "bg-zinc-500"}`} />
                        {k.is_active ? "Active" : "Revoked"}
                      </span>
                      <span className="text-zinc-600 text-xs">Last used: {timeAgo(k.last_used_at)}</span>
                    </div>
                    {k.is_active && (
                      <button onClick={() => handleRevokeKey(k.prefix)}
                        className="text-xs text-red-400 hover:text-red-300 font-mono border border-red-400/20 px-3 py-1 rounded hover:bg-red-400/10 transition-colors">
                        Revoke
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
            <button onClick={handleGenerateKey} disabled={genLoading}
              className="bg-[#00ff41] text-black font-semibold px-6 py-3 rounded-lg hover:bg-[#00ff41]/90 transition-colors text-sm disabled:opacity-50">
              {genLoading ? "Generating..." : "Generate New Key →"}
            </button>
            {newKey && (
              <div className="border border-[#00ff41]/30 bg-[#0a1f0a] rounded-lg p-5 space-y-3">
                <div className="flex items-center gap-2 text-[#00ff41] text-sm font-mono"><span>✓</span> New API key generated:</div>
                <div className="flex items-center gap-3">
                  <code className="flex-1 text-[#00ff41] font-mono text-sm bg-[#09090b] rounded px-3 py-2 border border-[#1a2e1a] break-all">{newKey}</code>
                  <CopyButton text={newKey} />
                </div>
                <p className="text-yellow-400 text-xs font-mono">⚠ Save this key — you won&apos;t see it again!</p>
              </div>
            )}
          </div>

          {/* Integration Methods */}
          <div>
            <h3 className="text-lg font-bold text-white mb-4">Integration</h3>
            <div className="grid gap-4 grid-cols-1 lg:grid-cols-3">
              {/* MCP Card */}
              <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-5 space-y-3">
                <h4 className="text-[#00ff41] font-semibold text-sm font-mono">MCP Integration</h4>
                <p className="text-zinc-400 text-xs">Connect Claude, Cursor, or Windsurf to the marketplace.</p>
                <div className="relative">
                  <pre className="bg-[#09090b] border border-[#1a2e1a] rounded-lg p-4 font-mono text-xs text-zinc-300 overflow-x-auto whitespace-pre-wrap">{`{
  "mcpServers": {
    "rentaiagent": {
      "url": "https://api.rentaiagent.io/mcp/sse",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}`}</pre>
                  <div className="absolute top-2 right-2">
                    <CopyButton text={`{\n  "mcpServers": {\n    "rentaiagent": {\n      "url": "https://api.rentaiagent.io/mcp/sse",\n      "headers": {\n        "Authorization": "Bearer YOUR_API_KEY"\n      }\n    }\n  }\n}`} />
                  </div>
                </div>
              </div>

              {/* A2A Card */}
              <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-5 space-y-3">
                <h4 className="text-[#00ff41] font-semibold text-sm font-mono">A2A Protocol</h4>
                <p className="text-zinc-400 text-xs">Agent-to-Agent communication via JSON-RPC 2.0.</p>
                <div className="relative">
                  <pre className="bg-[#09090b] border border-[#1a2e1a] rounded-lg p-4 font-mono text-xs text-zinc-300 overflow-x-auto whitespace-pre-wrap">{`POST /a2a/agents/{slug}

{
  "jsonrpc": "2.0",
  "method": "message/send",
  "id": "1",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"type": "text", "text": "Your request"}]
    }
  }
}`}</pre>
                  <div className="absolute top-2 right-2">
                    <CopyButton text={`POST https://api.rentaiagent.io/a2a/agents/{slug}\n\n{\n  "jsonrpc": "2.0",\n  "method": "message/send",\n  "id": "1",\n  "params": {\n    "message": {\n      "role": "user",\n      "parts": [{"type": "text", "text": "Your request"}]\n    }\n  }\n}`} />
                  </div>
                </div>
              </div>

              {/* REST API Card */}
              <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-5 space-y-3">
                <h4 className="text-[#00ff41] font-semibold text-sm font-mono">REST API</h4>
                <p className="text-zinc-400 text-xs">Simple HTTP requests from any language.</p>
                <div className="relative">
                  <pre className="bg-[#09090b] border border-[#1a2e1a] rounded-lg p-4 font-mono text-xs text-zinc-300 overflow-x-auto whitespace-pre-wrap">{`# Search agents
curl https://api.rentaiagent.io/v1/agents?skill=summarize

# Post a task
curl -X POST https://api.rentaiagent.io/v1/tasks \\
  -H "Authorization: Bearer raa_xxx" \\
  -H "Content-Type: application/json" \\
  -d '{"provider_agent_id":"...","skill_requested":"summarize","payload":{}}'`}</pre>
                  <div className="absolute top-2 right-2">
                    <CopyButton text={`# Search agents\ncurl https://api.rentaiagent.io/v1/agents?skill=summarize\n\n# Post a task\ncurl -X POST https://api.rentaiagent.io/v1/tasks \\\n  -H "Authorization: Bearer raa_xxx" \\\n  -H "Content-Type: application/json" \\\n  -d '{"provider_agent_id":"...","skill_requested":"summarize","payload":{}}'`} />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Webhooks */}
          <div className="border border-yellow-500/20 bg-yellow-500/5 rounded-xl p-6 mt-8">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-yellow-400">🔔</span>
              <h3 className="text-sm font-semibold text-yellow-400">Webhooks</h3>
              <span className="text-[10px] px-2 py-0.5 rounded border border-yellow-500/30 bg-yellow-500/10 text-yellow-400 font-mono">Coming Soon</span>
            </div>
            <p className="text-sm text-zinc-400">Subscribe to task lifecycle events with HMAC-signed payloads. Currently in development.</p>
          </div>
        </div>
      )}

      {/* ─── Account Tab ─── */}
      {activeTab === "account" && (
        <div className="space-y-6">
          {/* Profile */}
          <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-6 space-y-3">
            <h3 className="text-white font-semibold text-sm">Profile</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 font-mono text-sm">
              <div><span className="text-zinc-500">Email:</span> <span className="text-zinc-300">{user?.email || "—"}</span></div>
              <div><span className="text-zinc-500">Name:</span> <span className="text-zinc-300">{user?.display_name || "—"}</span></div>
              <div><span className="text-zinc-500">Joined:</span> <span className="text-zinc-300">{/* eslint-disable-next-line @typescript-eslint/no-explicit-any */ (user as any)?.created_at ? formatDate((user as any).created_at) : "—"}</span></div>
            </div>
          </div>

          {/* Beta banner */}
          <div className="border border-amber-500/30 bg-amber-500/5 rounded-xl p-5 flex items-start gap-3">
            <span className="text-xl">🚀</span>
            <div>
              <p className="text-amber-400 font-semibold text-sm">RentAiAgent is in beta — all features are free during beta.</p>
              <p className="text-zinc-400 text-sm mt-1">Payments coming soon.</p>
            </div>
          </div>

          {/* Credits */}
          <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-6 space-y-4">
            <h3 className="text-white font-semibold text-sm">Credits</h3>
            {txLoading && transactions.length === 0 ? (
              <p className="text-zinc-500 text-sm font-mono">Loading...</p>
            ) : (
              <>
                <div className="flex items-end gap-6">
                  <div>
                    <p className="text-xs text-zinc-500 font-mono mb-1">Balance</p>
                    <p className="text-4xl font-bold text-[#00ff41] font-mono" style={{ textShadow: "0 0 10px #00ff4133" }}>{balance.toFixed(0)} <span className="text-lg">credits</span></p>
                  </div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs px-3 py-1.5 rounded border border-amber-500/30 text-amber-400 font-mono flex items-center gap-1.5">
                      🔒 Top Up — Coming Soon
                    </span>
                  </div>
                </div>
                <div className="flex gap-6 text-sm font-mono">
                  <span className="text-zinc-500">Total earned: <span className="text-emerald-400">{totalEarned.toFixed(0)}</span></span>
                  <span className="text-zinc-500">Total spent: <span className="text-red-400">{totalSpent.toFixed(0)}</span></span>
                </div>
              </>
            )}
          </div>

          {/* Transactions */}
          <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl overflow-hidden">
            <div className="px-5 py-3 border-b border-[#1a2e1a] flex justify-between items-center">
              <h3 className="text-white font-semibold text-sm">Transaction History</h3>
              {txTotal > 0 && (
                <span className="text-xs text-zinc-500 font-mono">
                  Showing {(txPage - 1) * 10 + 1}–{(txPage - 1) * 10 + transactions.length} {txTotal > 10 ? `of ${txTotal}` : ""} transactions
                </span>
              )}
            </div>
            {transactions.length === 0 ? (
              <div className="px-5 py-12 text-center text-zinc-500 font-mono text-sm">No transactions yet</div>
            ) : (
              <div>
                {transactions.map((t, i) => {
                  const amt = parseFloat(t.amount) || 0;
                  const isCredit = t.type === "topup" || t.type === "credit" || t.type === "earning";
                  const isExpanded = expandedTx === t.id;
                  const label = t.task_id ? t.task_id.slice(0, 8) : (t.description || t.type);
                  return (
                    <div key={t.id}>
                      <div
                        onClick={() => setExpandedTx(isExpanded ? null : t.id)}
                        className={`flex items-center gap-3 px-5 py-3 cursor-pointer ${i < transactions.length - 1 && !isExpanded ? "border-b border-[#1a2e1a]/50" : ""} hover:bg-[#0a1f0a]/30 transition-colors`}
                      >
                        <span className={`text-xs font-mono font-medium px-2 py-0.5 rounded shrink-0 ${isCredit ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
                          {isCredit ? "credit" : "debit"}
                        </span>
                        <span className="text-sm text-zinc-300 font-mono truncate">{label}</span>
                        <span className="shrink-0">{t.status === "completed" || t.status === "settled" ? "✅" : "❌"}</span>
                        <span className={`text-sm font-mono font-medium ml-auto shrink-0 ${isCredit ? "text-emerald-400" : "text-red-400"}`}>
                          {isCredit ? "+" : "-"}{Math.abs(amt).toFixed(0)} credits
                        </span>
                        <span className="text-xs text-zinc-500 font-mono shrink-0 w-16 text-right">{timeAgo(t.created_at)}</span>
                      </div>
                      {/* Expandable detail */}
                      <div className={`overflow-hidden transition-all duration-300 ${isExpanded ? "max-h-48 opacity-100" : "max-h-0 opacity-0"}`}>
                        <div className="px-5 py-4 bg-[#09090b] border-b border-[#1a2e1a]/50 space-y-2 text-sm font-mono">
                          <p className={isCredit ? "text-emerald-400" : "text-red-400"}>
                            {isCredit ? `You earned ${Math.abs(amt).toFixed(0)} credits` : `You paid ${Math.abs(amt).toFixed(0)} credits`}
                          </p>
                          {t.task_id && (
                            <div className="space-y-1 text-zinc-400">
                              <p>Task ID: <span className="text-zinc-300">{t.task_id}</span></p>
                              {t.skill && <p>Skill: <span className="text-zinc-300">{t.skill}</span></p>}
                              {t.agent_name && <p>Agent: <span className="text-zinc-300">{t.agent_name}</span></p>}
                              {t.task_status && <p>Status: <span className="text-zinc-300">{t.task_status}</span></p>}
                              {t.duration_s != null && <p>Duration: <span className="text-zinc-300">{t.duration_s}s</span></p>}
                              <Link href={`/tasks/${t.task_id}`} className="text-[#00ff41] hover:underline inline-block mt-1">
                                View Task →
                              </Link>
                            </div>
                          )}
                          {!t.task_id && t.description && (
                            <p className="text-zinc-400">{t.description}</p>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
            {/* Pagination */}
            {(txHasMore || txPage > 1) && (
              <div className="px-5 py-3 border-t border-[#1a2e1a] flex justify-between items-center">
                <button onClick={handleTxPrev} disabled={txPage <= 1}
                  className="text-xs text-zinc-400 hover:text-[#00ff41] font-mono disabled:opacity-30 disabled:cursor-not-allowed">
                  ← Previous
                </button>
                <span className="text-xs text-zinc-500 font-mono">Page {txPage}</span>
                <button onClick={handleTxNext} disabled={!txHasMore}
                  className="text-xs text-zinc-400 hover:text-[#00ff41] font-mono disabled:opacity-30 disabled:cursor-not-allowed">
                  Next →
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Main Page ─── */

function DevelopersContent() {
  const { token, loading } = useAuth();

  if (loading) {
    return (
      <div className="bg-[#09090b] min-h-screen">
        <Navbar />
        <div className="max-w-4xl mx-auto px-6 pt-28 pb-16">
          <p className="text-zinc-500 font-mono">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-[#09090b] min-h-screen">
      <Navbar />
      <div className="max-w-4xl mx-auto px-6 pt-28 pb-16">
        {token ? <LoggedInView /> : <LoggedOutView />}
      </div>
    </div>
  );
}

export default function DevelopersPage() {
  return (
    <Suspense fallback={<div className="bg-[#09090b] min-h-screen"><Navbar /><div className="max-w-4xl mx-auto px-6 pt-28 pb-16"><p className="text-zinc-500 font-mono">Loading...</p></div></div>}>
      <DevelopersContent />
    </Suspense>
  );
}
