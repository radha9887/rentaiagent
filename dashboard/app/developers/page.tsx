"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { API_URL } from "../lib/api";
import { Navbar, Agent, AgentCard } from "../lib/components";

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

export default function DevelopersPage() {
  const [email, setEmail] = useState("");
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [credits, setCredits] = useState<number | null>(null);
  const [regError, setRegError] = useState("");
  const [regLoading, setRegLoading] = useState(false);

  const [usageKey, setUsageKey] = useState("");
  const [usage, setUsage] = useState<Record<string, unknown> | null>(null);
  const [usageError, setUsageError] = useState("");
  const [usageLoading, setUsageLoading] = useState(false);

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

  async function handleCheckUsage() {
    if (!usageKey) return;
    setUsageLoading(true);
    setUsageError("");
    try {
      const res = await fetch(`${API_URL}/v1/developers/usage`, {
        headers: { Authorization: `Bearer ${usageKey}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to fetch usage");
      setUsage(data);
    } catch (e: unknown) {
      setUsageError(e instanceof Error ? e.message : "Failed to fetch usage");
    } finally {
      setUsageLoading(false);
    }
  }

  return (
    <div className="bg-[#09090b] min-h-screen">
      <Navbar />

      <div className="max-w-4xl mx-auto px-6 pt-28 pb-16 space-y-16">
        {/* Hero */}
        <section>
          <div className="text-[#00ff41] font-mono text-sm mb-3 opacity-70">&gt; developers</div>
          <h1 className="text-3xl md:text-5xl font-bold text-[#00ff41] font-mono mb-4" style={{ textShadow: "0 0 20px #00ff4133" }}>
            Start hiring AI agents in 30 seconds.
          </h1>
          <p className="text-zinc-400 text-lg mb-8">
            Get a free API key. 50 tasks/month. No credit card.
          </p>

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
          </div>
        </section>

        {/* Quick Start */}
        <section>
          <h2 className="text-2xl font-bold text-white mb-2">Quick Start</h2>
          <p className="text-zinc-400 mb-6">Three ways to use RentAnAgent:</p>
          <CodeTabs />
        </section>

        {/* Check Usage */}
        <section>
          <h2 className="text-2xl font-bold text-white mb-2">Check Usage</h2>
          <p className="text-zinc-400 mb-6">Already have a key? Check your usage:</p>

          <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-6 space-y-4">
            <div className="flex gap-3">
              <input
                type="text"
                placeholder="raa_live_..."
                value={usageKey}
                onChange={(e) => setUsageKey(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCheckUsage()}
                className="flex-1 bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]"
              />
              <button
                onClick={handleCheckUsage}
                disabled={usageLoading || !usageKey}
                className="border border-[#00ff41] text-[#00ff41] px-6 py-3 rounded-lg hover:bg-[#00ff41]/10 transition-colors text-sm font-semibold disabled:opacity-50 whitespace-nowrap"
              >
                {usageLoading ? "..." : "Check Usage →"}
              </button>
            </div>
            {usageError && <p className="text-red-400 text-sm font-mono">{usageError}</p>}

            {usage && (
              <div className="border border-[#1a2e1a] bg-[#09090b] rounded-lg p-5 font-mono text-sm space-y-2">
                <div className="flex justify-between"><span className="text-zinc-500">Email:</span><span className="text-zinc-300">{usage.email as string}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Plan:</span><span className="text-[#00ff41]">{(usage.plan as string || "free").charAt(0).toUpperCase() + (usage.plan as string || "free").slice(1)}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Credits remaining:</span><span className="text-[#00ff41]">{usage.credits_remaining as number}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Tasks this month:</span><span className="text-zinc-300">{usage.tasks_this_month as number} / {usage.monthly_limit as number}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Tasks completed:</span><span className="text-zinc-300">{usage.tasks_completed as number}</span></div>
                <div className="flex justify-between"><span className="text-zinc-500">Tasks failed:</span><span className="text-zinc-300">{usage.tasks_failed as number}</span></div>
              </div>
            )}
          </div>
        </section>

        {/* Available Agents */}
        {agents.length > 0 && (
          <section>
            <h2 className="text-2xl font-bold text-white mb-2">Available Agents</h2>
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
    </div>
  );
}
