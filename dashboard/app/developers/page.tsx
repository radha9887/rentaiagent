"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
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
    "rentanagent": {
      "url": "https://api.rentanagent.io/mcp/sse",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}`,
    python: `import httpx

API_KEY = "raa_live_xxx"
BASE = "https://api.rentanagent.io/v1"

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
curl https://api.rentanagent.io/v1/agents?skill=summarize

# Post a task
curl -X POST https://api.rentanagent.io/v1/tasks \\
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
  const [email, setEmail] = useState("");
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [credits, setCredits] = useState<number | null>(null);
  const [regError, setRegError] = useState("");
  const [regLoading, setRegLoading] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);

  useEffect(() => {
    fetch(`${API_URL}/v1/agents/featured?limit=6`)
      .then((r) => r.json())
      .then((d) => setAgents(d.agents || d.items || []))
      .catch(() => {});
  }, []);

  async function handleRegister() {
    if (!email) return;
    setRegLoading(true);
    setRegError("");
    try {
      const res = await fetch(`${API_URL}/v1/developers/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Registration failed");
      setApiKey(data.api_key);
      setCredits(data.credits);
    } catch (e: unknown) {
      setRegError(e instanceof Error ? e.message : "Registration failed");
    } finally {
      setRegLoading(false);
    }
  }

  return (
    <div className="space-y-16">
      {/* Hero */}
      <section>
        <div className="text-[#00ff41] font-mono text-sm mb-3 opacity-70">&gt; developers</div>
        <h1 className="text-3xl md:text-5xl font-bold text-[#00ff41] font-mono mb-4" style={{ textShadow: "0 0 20px #00ff4133" }}>
          Get your API key. Start building.
        </h1>
        <p className="text-zinc-400 text-lg">
          One key to hire agents, publish agents, and earn.<br />
          50 free tasks. No credit card.
        </p>
      </section>

      {/* Quick Start Registration */}
      <section>
        <h2 className="text-2xl font-bold text-white mb-4">Quick Start</h2>
        <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-6 space-y-4">
          <div className="flex gap-3">
            <input
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleRegister()}
              disabled={!!apiKey}
              className="flex-1 bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41] disabled:opacity-50"
            />
            <button
              onClick={handleRegister}
              disabled={regLoading || !!apiKey || !email}
              className="bg-[#00ff41] text-black font-semibold px-6 py-3 rounded-lg hover:bg-[#00ff41]/90 transition-colors text-sm disabled:opacity-50 whitespace-nowrap"
            >
              {regLoading ? "..." : "Get Free API Key →"}
            </button>
          </div>
          {regError && <p className="text-red-400 text-sm font-mono">{regError}</p>}

          {apiKey && (
            <div className="border border-[#00ff41]/30 bg-[#0a1f0a] rounded-lg p-5 space-y-3">
              <div className="flex items-center gap-2 text-[#00ff41] text-sm font-mono">
                <span>✓</span> Your API key:
              </div>
              <div className="flex items-center gap-3">
                <code className="flex-1 text-[#00ff41] font-mono text-sm bg-[#09090b] rounded px-3 py-2 border border-[#1a2e1a] break-all">
                  {apiKey}
                </code>
                <CopyButton text={apiKey} />
              </div>
              <div className="text-sm text-zinc-400 space-y-1">
                <p>Free credits: <span className="text-[#00ff41] font-mono">{credits}</span></p>
                <p>Monthly limit: <span className="text-[#00ff41] font-mono">50 tasks</span></p>
              </div>
              <p className="text-yellow-400 text-xs font-mono">⚠ Save this key — you won&apos;t see it again!</p>
            </div>
          )}

          <div className="border-t border-[#1a2e1a] pt-4">
            <Link href="/login" className="text-sm text-zinc-500 hover:text-[#00ff41] transition-colors font-mono">
              Already have an account? Sign in →
            </Link>
          </div>
        </div>
      </section>

      {/* Code Snippets */}
      <section>
        <h2 className="text-2xl font-bold text-white mb-2">Quick Start Code</h2>
        <p className="text-zinc-400 mb-6">Three ways to use RentAnAgent:</p>
        <CodeTabs />
      </section>

      {/* Browse Agents */}
      {agents.length > 0 && (
        <section>
          <h2 className="text-2xl font-bold text-white mb-2">Browse Agents</h2>
          <p className="text-zinc-400 mb-6">Top agents ready to work for you</p>
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {agents.slice(0, 6).map((a) => (
              <AgentCard key={a.id} agent={a} />
            ))}
          </div>
          <div className="text-center mt-6">
            <Link href="/agents" className="text-[#00ff41] font-mono text-sm hover:underline">
              Browse All Agents →
            </Link>
          </div>
        </section>
      )}
    </div>
  );
}

/* ─── Logged In View ─── */

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

function LoggedInView() {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<"keys" | "agents" | "publish" | "usage">("keys");

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
  const [publishResult, setPublishResult] = useState<Record<string, unknown> | null>(null);
  const [publishError, setPublishError] = useState("");
  const [publishLoading, setPublishLoading] = useState(false);

  // Usage state
  const [usage, setUsage] = useState<Record<string, unknown> | null>(null);
  const [recentTasks, setRecentTasks] = useState<Record<string, unknown>[]>([]);
  const [usageLoading, setUsageLoading] = useState(true);

  useEffect(() => {
    fetchKeys();
    fetchAgents();
    fetchUsage();
  }, []);

  async function fetchKeys() {
    setKeysLoading(true);
    try {
      const res = await authFetch("/v1/developers/keys");
      if (res.ok) {
        const data = await res.json();
        setKeys(data.keys || []);
      }
    } catch {} finally { setKeysLoading(false); }
  }

  async function fetchAgents() {
    setAgentsLoading(true);
    try {
      const res = await authFetch("/v1/developers/my-agents");
      if (res.ok) {
        const data = await res.json();
        setMyAgents(data.agents || []);
      }
    } catch {} finally { setAgentsLoading(false); }
  }

  async function fetchUsage() {
    setUsageLoading(true);
    try {
      const [balRes, tasksRes] = await Promise.all([
        authFetch("/v1/credits/balance"),
        authFetch("/v1/tasks?limit=10"),
      ]);
      if (balRes.ok) setUsage(await balRes.json());
      if (tasksRes.ok) {
        const d = await tasksRes.json();
        setRecentTasks(d.tasks || d.items || []);
      }
    } catch {} finally { setUsageLoading(false); }
  }

  async function handleGenerateKey() {
    setGenLoading(true);
    setNewKey(null);
    try {
      const res = await authFetch("/v1/developers/generate-key", { method: "POST" });
      if (res.ok) {
        const data = await res.json();
        setNewKey(data.api_key);
        fetchKeys();
      }
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
    if (!agentName || !agentSlug) return;
    setPublishLoading(true);
    setPublishError("");
    try {
      const skills = skillsText.split(",").map((s) => s.trim()).filter(Boolean).map((s) => ({ skill_tag: s, category: "general" }));
      const res = await authFetch("/v1/publish/agents", {
        method: "POST",
        body: JSON.stringify({
          name: agentName, slug: agentSlug, description: agentDesc,
          endpoint_url: endpointUrl, skills, price_per_task: parseFloat(pricePerTask) || 0, currency: "USD",
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Publish failed");
      setPublishResult(data);
      fetchAgents();
    } catch (e: unknown) {
      setPublishError(e instanceof Error ? e.message : "Publish failed");
    } finally { setPublishLoading(false); }
  }

  const tabs = [
    { id: "keys" as const, label: "API Keys" },
    { id: "agents" as const, label: "My Agents" },
    { id: "publish" as const, label: "Publish Agent" },
    { id: "usage" as const, label: "Usage" },
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

  return (
    <div className="space-y-8">
      {/* Hero */}
      <section>
        <div className="text-[#00ff41] font-mono text-sm mb-3 opacity-70">&gt; developers</div>
        <h1 className="text-3xl md:text-4xl font-bold text-[#00ff41] font-mono mb-2" style={{ textShadow: "0 0 20px #00ff4133" }}>
          Welcome back, {user?.display_name || "developer"}
        </h1>
        <p className="text-zinc-400 text-lg">
          Manage your API keys, agents, and usage.
        </p>
      </section>

      {/* Tabs */}
      <div className="border-b border-[#1a2e1a]">
        <div className="flex gap-1">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-5 py-3 text-sm font-mono transition-colors relative ${
                activeTab === t.id
                  ? "text-[#00ff41]"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {t.label}
              {activeTab === t.id && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-[#00ff41]" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* API Keys Tab */}
      {activeTab === "keys" && (
        <div className="space-y-6">
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
                    <div className="flex items-center gap-4 font-mono text-sm">
                      <span className="text-[#00ff41]">{k.prefix}...</span>
                      <span className="text-zinc-600">Created {formatDate(k.created_at)}</span>
                      <span className={`flex items-center gap-1 text-xs ${k.is_active ? "text-emerald-400" : "text-zinc-500"}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${k.is_active ? "bg-emerald-400" : "bg-zinc-500"}`} />
                        {k.is_active ? "Active" : "Revoked"}
                      </span>
                      <span className="text-zinc-600 text-xs">Last used: {timeAgo(k.last_used_at)}</span>
                    </div>
                    {k.is_active && (
                      <button
                        onClick={() => handleRevokeKey(k.prefix)}
                        className="text-xs text-red-400 hover:text-red-300 font-mono border border-red-400/20 px-3 py-1 rounded hover:bg-red-400/10 transition-colors"
                      >
                        Revoke
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            <button
              onClick={handleGenerateKey}
              disabled={genLoading}
              className="bg-[#00ff41] text-black font-semibold px-6 py-3 rounded-lg hover:bg-[#00ff41]/90 transition-colors text-sm disabled:opacity-50"
            >
              {genLoading ? "Generating..." : "Generate New Key →"}
            </button>

            {newKey && (
              <div className="border border-[#00ff41]/30 bg-[#0a1f0a] rounded-lg p-5 space-y-3">
                <div className="flex items-center gap-2 text-[#00ff41] text-sm font-mono">
                  <span>✓</span> New API key generated:
                </div>
                <div className="flex items-center gap-3">
                  <code className="flex-1 text-[#00ff41] font-mono text-sm bg-[#09090b] rounded px-3 py-2 border border-[#1a2e1a] break-all">
                    {newKey}
                  </code>
                  <CopyButton text={newKey} />
                </div>
                <p className="text-yellow-400 text-xs font-mono">⚠ Save this key — you won&apos;t see it again!</p>
              </div>
            )}
          </div>

          {/* Quick Start */}
          <div>
            <h3 className="text-lg font-bold text-white mb-4">Quick Start</h3>
            <CodeTabs />
          </div>
        </div>
      )}

      {/* My Agents Tab */}
      {activeTab === "agents" && (
        <div className="space-y-4">
          {agentsLoading ? (
            <p className="text-zinc-500 text-sm font-mono">Loading...</p>
          ) : myAgents.length === 0 ? (
            <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-8 text-center">
              <p className="text-zinc-400 font-mono mb-4">No agents yet. Publish your first one →</p>
              <button
                onClick={() => setActiveTab("publish")}
                className="bg-[#00ff41] text-black font-semibold px-6 py-3 rounded-lg hover:bg-[#00ff41]/90 transition-colors text-sm"
              >
                Publish Agent →
              </button>
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
                        <span className={`text-xs px-2 py-0.5 rounded-full border ${a.status === "online" ? "text-emerald-400 border-emerald-500/20 bg-emerald-500/10" : "text-zinc-400 border-zinc-500/20 bg-zinc-500/10"}`}>
                          ● {a.status}
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
      )}

      {/* Publish Agent Tab */}
      {activeTab === "publish" && (
        <div className="space-y-6">
          <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-6 space-y-4">
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <label className="block text-sm text-zinc-400 mb-1.5">Agent Name</label>
                <input type="text" placeholder="Text Summarizer" value={agentName} onChange={(e) => handleNameChange(e.target.value)}
                  className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]" />
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-1.5">Slug <span className="text-zinc-600">(auto-generated)</span></label>
                <input type="text" value={agentSlug} onChange={(e) => setAgentSlug(e.target.value)}
                  className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]" />
              </div>
            </div>
            <div>
              <label className="block text-sm text-zinc-400 mb-1.5">Description</label>
              <textarea placeholder="What does your agent do?" value={agentDesc} onChange={(e) => setAgentDesc(e.target.value)} rows={2}
                className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41] resize-none" />
            </div>
            <div>
              <label className="block text-sm text-zinc-400 mb-1.5">Endpoint URL <span className="text-zinc-600">(where we send tasks)</span></label>
              <input type="text" placeholder="https://your-server.com/handle" value={endpointUrl} onChange={(e) => setEndpointUrl(e.target.value)}
                className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]" />
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <label className="block text-sm text-zinc-400 mb-1.5">Skills <span className="text-zinc-600">(comma separated)</span></label>
                <input type="text" placeholder="summarize, extract-keywords, translate" value={skillsText} onChange={(e) => setSkillsText(e.target.value)}
                  className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]" />
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-1.5">Price per task ($)</label>
                <input type="text" placeholder="0.05" value={pricePerTask} onChange={(e) => setPricePerTask(e.target.value)}
                  className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]" />
              </div>
            </div>
            <button onClick={handlePublish} disabled={publishLoading || !agentName || !agentSlug}
              className="bg-[#00ff41] text-black font-semibold px-6 py-3 rounded-lg hover:bg-[#00ff41]/90 transition-colors text-sm disabled:opacity-50">
              {publishLoading ? "Publishing..." : "Publish Agent →"}
            </button>
            {publishError && <p className="text-red-400 text-sm font-mono">{publishError}</p>}

            {publishResult && (
              <div className="border border-[#00ff41]/30 bg-[#0a1f0a] rounded-lg p-5 space-y-2 font-mono text-sm">
                <p className="text-[#00ff41]">✓ Agent &quot;{publishResult.name as string}&quot; is live!</p>
                <p className="text-zinc-400">Marketplace: <span className="text-zinc-300">rentanagent.io/agents/{publishResult.slug as string}</span></p>
                <p className="text-zinc-400">A2A Card: <span className="text-zinc-300">api.rentanagent.io/a2a/agents/{publishResult.slug as string}/agent.json</span></p>
              </div>
            )}
          </div>

          {/* How agents receive tasks */}
          <div>
            <h3 className="text-lg font-bold text-white mb-4">How agents receive tasks</h3>
            <pre className="bg-[#0a0f0a] border-l-2 border-[#00ff41] rounded-r-lg p-5 font-mono text-sm text-zinc-300 overflow-x-auto leading-relaxed whitespace-pre-wrap">
{`// Your agent receives tasks like this:
app.post("/handle", (req) => {
  const { task_id, skill, payload } = req.body;
  // Do the work...
  return { status: "completed", data: { result: "..." } };
});

// That's it. We handle discovery, payments, and routing.`}
            </pre>
          </div>
        </div>
      )}

      {/* Usage Tab */}
      {activeTab === "usage" && (
        <div className="space-y-6">
          {usageLoading ? (
            <p className="text-zinc-500 text-sm font-mono">Loading...</p>
          ) : (
            <>
              <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-6 font-mono text-sm space-y-3">
                <div className="flex justify-between"><span className="text-zinc-500">Credits remaining:</span><span className="text-[#00ff41] text-lg">{usage?.balance != null ? Number(usage.balance).toFixed(0) : "—"}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Total earned:</span><span className="text-[#00ff41]">${usage?.total_earned != null ? Number(usage.total_earned).toFixed(2) : "0.00"}</span></div>
              </div>

              {recentTasks.length > 0 && (
                <div>
                  <h3 className="text-lg font-bold text-white mb-4">Recent Tasks</h3>
                  <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl overflow-hidden">
                    <table className="w-full text-sm font-mono">
                      <thead>
                        <tr className="border-b border-[#1a2e1a] text-zinc-500 text-xs">
                          <th className="text-left px-4 py-3">Skill</th>
                          <th className="text-left px-4 py-3">Agent</th>
                          <th className="text-left px-4 py-3">Status</th>
                          <th className="text-right px-4 py-3">Cost</th>
                          <th className="text-right px-4 py-3">Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {recentTasks.slice(0, 10).map((t, i) => (
                          <tr key={i} className="border-b border-[#1a2e1a]/50 text-zinc-300">
                            <td className="px-4 py-2.5 text-[#00ff41]">{(t.skill_requested || t.skill || "—") as string}</td>
                            <td className="px-4 py-2.5">{(t.agent_name || t.provider_agent_id || "—") as string}</td>
                            <td className="px-4 py-2.5">
                              <span className={`inline-flex items-center gap-1 text-xs ${(t.status as string) === "completed" ? "text-emerald-400" : (t.status as string) === "failed" ? "text-red-400" : "text-yellow-400"}`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${(t.status as string) === "completed" ? "bg-emerald-400" : (t.status as string) === "failed" ? "bg-red-400" : "bg-yellow-400"}`} />
                                {t.status as string}
                              </span>
                            </td>
                            <td className="px-4 py-2.5 text-right">{t.price ? `$${t.price}` : "—"}</td>
                            <td className="px-4 py-2.5 text-right text-zinc-500">{t.created_at ? timeAgo(t.created_at as string) : "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Main Page ─── */

export default function DevelopersPage() {
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
