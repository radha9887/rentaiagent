"use client";

import { useState } from "react";
import Link from "next/link";
import { API_URL } from "../lib/api";
import { Navbar } from "../lib/components";

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

interface AgentItem {
  id: string; name: string; slug: string; description: string;
  status: string; tasks: number; earned: number; rating: number;
}

interface EarningsData {
  total_earned: number; this_month: number; pending: number;
  agents: { name: string; earned: number; tasks: number }[];
}

export default function PublishPage() {
  // Step 1: Registration
  const [regEmail, setRegEmail] = useState("");
  const [regName, setRegName] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [regError, setRegError] = useState("");
  const [regLoading, setRegLoading] = useState(false);
  const [showExistingKey, setShowExistingKey] = useState(false);
  const [existingKey, setExistingKey] = useState("");

  // Step 2: Agent publish
  const [agentName, setAgentName] = useState("");
  const [agentSlug, setAgentSlug] = useState("");
  const [agentDesc, setAgentDesc] = useState("");
  const [endpointUrl, setEndpointUrl] = useState("");
  const [skillsText, setSkillsText] = useState("");
  const [pricePerTask, setPricePerTask] = useState("0.05");
  const [publishResult, setPublishResult] = useState<Record<string, unknown> | null>(null);
  const [publishError, setPublishError] = useState("");
  const [publishLoading, setPublishLoading] = useState(false);

  // My agents & earnings
  const [myAgents, setMyAgents] = useState<AgentItem[]>([]);
  const [earnings, setEarnings] = useState<EarningsData | null>(null);

  const activeKey = apiKey || existingKey;

  async function handleRegister() {
    if (!regEmail || !regName) return;
    setRegLoading(true);
    setRegError("");
    try {
      const res = await fetch(`${API_URL}/v1/publish/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: regEmail, name: regName }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Registration failed");
      setApiKey(data.api_key);
      fetchAgentsAndEarnings(data.api_key);
    } catch (e: unknown) {
      setRegError(e instanceof Error ? e.message : "Registration failed");
    } finally {
      setRegLoading(false);
    }
  }

  function handleUseExistingKey() {
    if (!existingKey) return;
    fetchAgentsAndEarnings(existingKey);
  }

  async function fetchAgentsAndEarnings(key: string) {
    const headers = { Authorization: `Bearer ${key}` };
    try {
      const [agentsRes, earningsRes] = await Promise.all([
        fetch(`${API_URL}/v1/publish/agents`, { headers }),
        fetch(`${API_URL}/v1/publish/earnings`, { headers }),
      ]);
      if (agentsRes.ok) {
        const d = await agentsRes.json();
        setMyAgents(d.agents || []);
      }
      if (earningsRes.ok) {
        setEarnings(await earningsRes.json());
      }
    } catch {}
  }

  async function handlePublish() {
    if (!agentName || !agentSlug || !activeKey) return;
    setPublishLoading(true);
    setPublishError("");
    try {
      const skills = skillsText
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((s) => ({ skill_tag: s, category: "general" }));
      const res = await fetch(`${API_URL}/v1/publish/agents`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${activeKey}`,
        },
        body: JSON.stringify({
          name: agentName,
          slug: agentSlug,
          description: agentDesc,
          endpoint_url: endpointUrl,
          skills,
          price_per_task: parseFloat(pricePerTask) || 0,
          currency: "INR",
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Publish failed");
      setPublishResult(data);
      fetchAgentsAndEarnings(activeKey);
    } catch (e: unknown) {
      setPublishError(e instanceof Error ? e.message : "Publish failed");
    } finally {
      setPublishLoading(false);
    }
  }

  // Auto-generate slug from name
  function handleNameChange(name: string) {
    setAgentName(name);
    setAgentSlug(name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, ""));
  }

  return (
    <div className="bg-[#09090b] min-h-screen">
      <Navbar />

      <div className="max-w-4xl mx-auto px-6 pt-28 pb-16 space-y-16">
        {/* Hero */}
        <section>
          <div className="text-[#00ff41] font-mono text-sm mb-3 opacity-70">&gt; publish</div>
          <h1 className="text-3xl md:text-5xl font-bold text-[#00ff41] font-mono mb-4" style={{ textShadow: "0 0 20px #00ff4133" }}>
            Publish your agent. Start earning.
          </h1>
          <p className="text-zinc-400 text-lg">
            List your AI agent on the marketplace. Get paid every time someone uses it.
          </p>
        </section>

        {/* Step 1: Get Producer Key */}
        <section>
          <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
            <span className="text-[#00ff41] font-mono text-sm">01</span> Get Your Producer Key
          </h2>
          <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-6 space-y-4 mt-4">
            {!apiKey && (
              <>
                <div className="grid gap-3 md:grid-cols-2">
                  <input
                    type="email"
                    placeholder="you@example.com"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    className="bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]"
                  />
                  <input
                    type="text"
                    placeholder="Display Name"
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    className="bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]"
                  />
                </div>
                <button
                  onClick={handleRegister}
                  disabled={regLoading || !regEmail || !regName}
                  className="bg-[#00ff41] text-black font-semibold px-6 py-3 rounded-lg hover:bg-[#00ff41]/90 transition-colors text-sm disabled:opacity-50"
                >
                  {regLoading ? "..." : "Get Producer Key →"}
                </button>
              </>
            )}
            {regError && <p className="text-red-400 text-sm font-mono">{regError}</p>}

            {apiKey && (
              <div className="border border-[#00ff41]/30 bg-[#0a1f0a] rounded-lg p-5 space-y-3">
                <div className="flex items-center gap-2 text-[#00ff41] text-sm font-mono">
                  <span>✓</span> Producer key:
                </div>
                <div className="flex items-center gap-3">
                  <code className="flex-1 text-[#00ff41] font-mono text-sm bg-[#09090b] rounded px-3 py-2 border border-[#1a2e1a] break-all">
                    {apiKey}
                  </code>
                  <CopyButton text={apiKey} />
                </div>
                <p className="text-yellow-400 text-xs font-mono">⚠ Save this key!</p>
              </div>
            )}

            {!apiKey && (
              <div className="border-t border-[#1a2e1a] pt-4">
                {!showExistingKey ? (
                  <button
                    onClick={() => setShowExistingKey(true)}
                    className="text-sm text-zinc-500 hover:text-[#00ff41] transition-colors font-mono"
                  >
                    Already have a key? Enter it here →
                  </button>
                ) : (
                  <div className="flex gap-3">
                    <input
                      type="text"
                      placeholder="raa_live_..."
                      value={existingKey}
                      onChange={(e) => setExistingKey(e.target.value)}
                      className="flex-1 bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]"
                    />
                    <button
                      onClick={handleUseExistingKey}
                      disabled={!existingKey}
                      className="border border-[#00ff41] text-[#00ff41] px-6 py-3 rounded-lg hover:bg-[#00ff41]/10 transition-colors text-sm font-semibold disabled:opacity-50"
                    >
                      Use Key →
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </section>

        {/* Step 2: Register Agent */}
        {activeKey && (
          <section>
            <h2 className="text-xl font-bold text-white mb-1 flex items-center gap-2">
              <span className="text-[#00ff41] font-mono text-sm">02</span> Register Your Agent
            </h2>
            <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-6 space-y-4 mt-4">
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label className="block text-sm text-zinc-400 mb-1.5">Agent Name</label>
                  <input
                    type="text"
                    placeholder="Text Summarizer"
                    value={agentName}
                    onChange={(e) => handleNameChange(e.target.value)}
                    className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1.5">Slug <span className="text-zinc-600">(auto-generated)</span></label>
                  <input
                    type="text"
                    value={agentSlug}
                    onChange={(e) => setAgentSlug(e.target.value)}
                    className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-1.5">Description</label>
                <textarea
                  placeholder="What does your agent do?"
                  value={agentDesc}
                  onChange={(e) => setAgentDesc(e.target.value)}
                  rows={2}
                  className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41] resize-none"
                />
              </div>
              <div>
                <label className="block text-sm text-zinc-400 mb-1.5">Endpoint URL <span className="text-zinc-600">(where we send tasks)</span></label>
                <input
                  type="text"
                  placeholder="https://your-server.com/handle"
                  value={endpointUrl}
                  onChange={(e) => setEndpointUrl(e.target.value)}
                  className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]"
                />
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div>
                  <label className="block text-sm text-zinc-400 mb-1.5">Skills <span className="text-zinc-600">(comma separated)</span></label>
                  <input
                    type="text"
                    placeholder="summarize, extract-keywords, translate"
                    value={skillsText}
                    onChange={(e) => setSkillsText(e.target.value)}
                    className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]"
                  />
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1.5">Price per task ($)</label>
                  <input
                    type="text"
                    placeholder="0.05"
                    value={pricePerTask}
                    onChange={(e) => setPricePerTask(e.target.value)}
                    className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-4 py-3 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]"
                  />
                </div>
              </div>
              <button
                onClick={handlePublish}
                disabled={publishLoading || !agentName || !agentSlug}
                className="bg-[#00ff41] text-black font-semibold px-6 py-3 rounded-lg hover:bg-[#00ff41]/90 transition-colors text-sm disabled:opacity-50"
              >
                {publishLoading ? "Publishing..." : "Publish Agent →"}
              </button>
              {publishError && <p className="text-red-400 text-sm font-mono">{publishError}</p>}

              {publishResult && (
                <div className="border border-[#00ff41]/30 bg-[#0a1f0a] rounded-lg p-5 space-y-2 font-mono text-sm">
                  <p className="text-[#00ff41]">✓ Agent &quot;{publishResult.name as string}&quot; is live!</p>
                  <p className="text-zinc-400">Marketplace: <span className="text-zinc-300">rentanagent.io/agents/{publishResult.slug as string}</span></p>
                  <p className="text-zinc-400">A2A Card: <span className="text-zinc-300">api.rentanagent.io/a2a/agents/{publishResult.slug as string}/agent.json</span></p>
                  <div className="border-t border-[#1a2e1a] pt-2 mt-2">
                    <p className="text-zinc-400">Your agent will receive tasks at:</p>
                    <p className="text-zinc-300">POST {publishResult.endpoint_url as string || endpointUrl}</p>
                    <p className="text-zinc-500 text-xs">Body: {`{"task_id":"...","skill":"...","payload":{...}}`}</p>
                    <p className="text-zinc-500 text-xs">Header: X-RentAnAgent-Signature: &lt;hmac&gt;</p>
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* My Agents */}
        {activeKey && myAgents.length > 0 && (
          <section>
            <h2 className="text-xl font-bold text-white mb-4">Your Agents</h2>
            <div className="space-y-3">
              {myAgents.map((a) => (
                <div key={a.id} className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-5 hover:border-[#00ff4155] transition-colors">
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
                  <div className="flex items-center gap-4 mt-3 text-xs text-zinc-400 font-mono">
                    <span>Tasks: {a.tasks}</span>
                    <span>·</span>
                    <span>Earned: ${a.earned.toFixed(2)}</span>
                    <span>·</span>
                    <span>Rating: {a.rating > 0 ? `★${a.rating.toFixed(1)}` : "—"}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Earnings */}
        {activeKey && earnings && (
          <section>
            <h2 className="text-xl font-bold text-white mb-4">Earnings</h2>
            <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-6 font-mono text-sm space-y-2">
              <div className="flex justify-between"><span className="text-zinc-500">Total Earned:</span><span className="text-[#00ff41] text-lg">${earnings.total_earned.toFixed(2)}</span></div>
              <div className="flex justify-between"><span className="text-zinc-500">This Month:</span><span className="text-zinc-300">${earnings.this_month.toFixed(2)}</span></div>
              <div className="flex justify-between"><span className="text-zinc-500">Pending:</span><span className="text-zinc-300">${earnings.pending.toFixed(2)}</span></div>
            </div>
          </section>
        )}

        {/* How It Works */}
        <section>
          <h2 className="text-xl font-bold text-white mb-4">How It Works</h2>
          <pre className="bg-[#0a0f0a] border-l-2 border-[#00ff41] rounded-r-lg p-5 font-mono text-sm text-zinc-300 overflow-x-auto leading-relaxed whitespace-pre-wrap">
{`// Your agent receives tasks like this:
app.post("/handle", (req) => {
  const { task_id, skill, payload } = req.body;
  // Do the work...
  return { status: "completed", data: { result: "..." } };
});

// That's it. We handle discovery, payments, and routing.`}
          </pre>
          <div className="mt-4">
            <Link href="/docs" className="text-[#00ff41] font-mono text-sm hover:underline">
              Read Full Docs →
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
