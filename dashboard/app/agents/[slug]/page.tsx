"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getAgentPublic, getAgentRatingsPublic, createTask, API_URL } from "../../lib/api";
import { Navbar, timeAgo } from "../../lib/components";

interface Skill { id: string; skill_tag: string; category?: string; proficiency: number; task_count: number; success_rate: number }
interface Stats { total_tasks: number; completed_tasks: number; failed_tasks: number; avg_rating: number; avg_response_ms: number; acceptance_rate: number; total_earned: string; rating_count: number }
interface Rating { id: string; overall_score: number; feedback?: string; created_at: string }
interface AgentData {
  id: string; name: string; slug: string; description?: string; status: string;
  pricing_model: string; price_per_task: string; currency: string;
  protocols: string[]; framework?: string; trust_tier: string; skills: Skill[]; stats?: Stats;
  is_external?: boolean;
  agent_card?: Record<string, unknown>;
  capabilities?: { streaming?: boolean; push_notifications?: boolean };
  provider_info?: { name?: string; url?: string };
  verification_status?: string;
  last_health_check?: string;
  endpoint_url?: string;
}

const TIER_COLORS: Record<string, string> = {
  new: "text-zinc-500 border-zinc-500/30 bg-zinc-500/10",
  bronze: "text-amber-400 border-amber-400/30 bg-amber-400/10",
  silver: "text-slate-300 border-slate-300/30 bg-slate-300/10",
  gold: "text-yellow-400 border-yellow-400/30 bg-yellow-400/10",
  platinum: "text-purple-400 border-purple-400/30 bg-purple-400/10",
};

export default function AgentDetailPage() {
  const { slug } = useParams();
  const router = useRouter();
  const hireRef = useRef<HTMLDivElement>(null);
  const [agent, setAgent] = useState<AgentData | null>(null);
  const [ratings, setRatings] = useState<Rating[]>([]);
  const [loading, setLoading] = useState(true);
  const [loggedIn, setLoggedIn] = useState(false);

  // Quick hire state
  const [selectedSkill, setSelectedSkill] = useState("");
  const [payload, setPayload] = useState('{\n  "text": "Your text here..."\n}');
  const [posting, setPosting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoggedIn(!!localStorage.getItem("jwt"));
    if (!slug) return;
    Promise.allSettled([
      getAgentPublic(slug as string),
      getAgentRatingsPublic(slug as string),
    ]).then(([a, r]) => {
      if (a.status === "fulfilled") {
        setAgent(a.value);
        if (a.value.skills?.length > 0) setSelectedSkill(a.value.skills[0].skill_tag);
      }
      if (r.status === "fulfilled") {
        const d = r.value;
        setRatings(d.items || (Array.isArray(d) ? d : []));
      }
    }).finally(() => setLoading(false));
  }, [slug]);

  const price = parseFloat(agent?.price_per_task || "0");
  const fee = price * 0.15;
  const total = price + fee;
  const curr = agent?.currency === "INR" ? "₹" : "$";
  const tier = agent?.trust_tier?.toLowerCase() || "new";
  const avgMs = agent?.stats?.avg_response_ms || 0;
  const tasks = agent?.stats?.total_tasks || 0;
  const rating = agent?.stats?.avg_rating || 0;
  const ratingCount = agent?.stats?.rating_count || 0;
  const successRate = agent?.stats?.acceptance_rate || 0;

  const handleHire = async () => {
    if (!agent) return;
    setError("");
    setPosting(true);
    try {
      let parsed: Record<string, unknown> | undefined;
      if (payload.trim()) {
        try { parsed = JSON.parse(payload); } catch { setError("Invalid JSON payload"); setPosting(false); return; }
      }
      const task = await createTask({
        provider_agent_id: agent.id,
        skill_requested: selectedSkill,
        payload: parsed,
      });
      router.push(`/tasks/${task.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setPosting(false);
    }
  };

  if (loading) return (
    <div className="bg-[#09090b] min-h-screen">
      <Navbar />
      <div className="max-w-4xl mx-auto px-6 pt-24"><p className="text-zinc-500 font-mono">Loading agent...</p></div>
    </div>
  );

  if (!agent) return (
    <div className="bg-[#09090b] min-h-screen">
      <Navbar />
      <div className="max-w-4xl mx-auto px-6 pt-24">
        <p className="text-zinc-400 font-mono">Agent not found</p>
        <Link href="/agents" className="text-[#00ff41] text-sm mt-4 inline-block hover:underline">← Back to marketplace</Link>
      </div>
    </div>
  );

  return (
    <div className="bg-[#09090b] min-h-screen">
      <Navbar />

      <div className="max-w-4xl mx-auto px-6 pt-24 pb-16 space-y-6">
        {/* Header */}
        <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6 md:p-8">
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-[#00ff41] text-xl">⬡</span>
                <h1 className="text-2xl md:text-3xl font-bold text-white">{agent.name}</h1>
                {agent.is_external && <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">External Agent 🌐</span>}
                <span className={`text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded border ${TIER_COLORS[tier] || TIER_COLORS.new}`}>{tier}</span>
                <span className={`inline-flex items-center gap-1.5 text-xs ${agent.status === "online" || agent.status === "active" ? "text-emerald-400" : "text-zinc-500"}`}>
                  <span className={`w-2 h-2 rounded-full ${agent.status === "online" || agent.status === "active" ? "bg-emerald-400" : "bg-zinc-500"}`} />
                  {agent.status}
                </span>
              </div>
              <p className="text-sm text-zinc-500 font-mono">@{agent.slug}</p>
              {agent.description && <p className="text-sm text-zinc-400 max-w-2xl">{agent.description}</p>}
              <div className="flex flex-wrap items-center gap-3 text-sm text-zinc-400 pt-1">
                <span className="text-[#00ff41] font-semibold">{curr}{price}/task</span>
                {rating > 0 && <><span className="text-zinc-600">·</span><span><span className="text-yellow-400">★</span>{rating.toFixed(1)} ({ratingCount} reviews)</span></>}
                {avgMs > 0 && <><span className="text-zinc-600">·</span><span>⚡{(avgMs / 1000).toFixed(1)}s avg</span></>}
                <span className="text-zinc-600">·</span><span>{tasks.toLocaleString()} tasks</span>
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-3 mt-5">
            <button onClick={() => hireRef.current?.scrollIntoView({ behavior: "smooth" })}
              className="px-5 py-2.5 bg-[#00ff41] text-black font-semibold rounded-lg text-sm hover:bg-[#00ff41]/90 transition-colors">
              Hire This Agent →
            </button>
            <a href="#integration" className="px-5 py-2.5 border border-[#1a2e1a] text-[#00ff41] rounded-lg text-sm hover:bg-[#0a1f0a] hover:border-[#00ff4155] transition-colors">
              View API Docs
            </a>
          </div>
        </div>

        {/* Skills */}
        {agent.skills?.length > 0 && (
          <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
            <h2 className="text-sm text-zinc-400 font-mono mb-4">// Skills</h2>
            <div className="flex flex-wrap gap-3">
              {agent.skills.map(s => (
                <div key={s.skill_tag} className="border border-[#1a2e1a] bg-[#09090b] rounded-lg px-4 py-3 hover:border-[#00ff4155] transition-colors">
                  <div className="text-sm text-[#00ff41] font-mono font-semibold">{s.skill_tag}</div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-zinc-500">
                    {s.category && <span>{s.category}</span>}
                    {s.proficiency > 0 && <><span>·</span><span>{(s.proficiency * 100).toFixed(1)}%</span></>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Quick Hire */}
        <div ref={hireRef} className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
          <h2 className="text-sm text-zinc-400 font-mono mb-4">// Quick Hire</h2>
          {loggedIn ? (
            <div className="space-y-4">
              {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg p-3">{error}</div>}
              {agent.skills?.length > 0 && (
                <div>
                  <label className="block text-sm text-zinc-400 mb-1.5">Select skill</label>
                  <select value={selectedSkill} onChange={e => setSelectedSkill(e.target.value)}
                    className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]">
                    {agent.skills.map(s => <option key={s.skill_tag} value={s.skill_tag}>{s.skill_tag}</option>)}
                  </select>
                </div>
              )}
              <div>
                <label className="block text-sm text-zinc-400 mb-1.5">Payload (JSON)</label>
                <textarea value={payload} onChange={e => setPayload(e.target.value)} rows={4}
                  className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]" />
              </div>
              <div className="text-sm text-zinc-400 font-mono">
                Estimated cost: <span className="text-white">{curr}{price.toFixed(2)}</span> + <span className="text-zinc-500">{curr}{fee.toFixed(2)} fee</span> = <span className="text-[#00ff41] font-semibold">{curr}{total.toFixed(2)}</span>
              </div>
              <button onClick={handleHire} disabled={posting}
                className="px-5 py-2.5 bg-[#00ff41] text-black font-semibold rounded-lg text-sm hover:bg-[#00ff41]/90 transition-colors disabled:opacity-50">
                {posting ? "Posting..." : "Post Task →"}
              </button>
            </div>
          ) : (
            <div className="text-center py-6">
              <p className="text-zinc-400 mb-3">Sign in to hire this agent</p>
              <Link href="/login" className="px-5 py-2.5 border border-[#00ff41] text-[#00ff41] rounded-lg text-sm hover:bg-[#00ff41]/10 transition-colors inline-block">
                Sign In →
              </Link>
            </div>
          )}
        </div>

        {/* Stats */}
        {agent.stats && (
          <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
            <h2 className="text-sm text-zinc-400 font-mono mb-4">// Stats</h2>
            <div className="grid grid-cols-3 gap-4 text-center mb-4">
              <div>
                <div className="text-2xl font-semibold text-[#00ff41] font-mono" style={{ textShadow: "0 0 6px #00ff4144" }}>{tasks.toLocaleString()}</div>
                <div className="text-xs text-zinc-500 mt-1">Tasks</div>
              </div>
              <div>
                <div className="text-2xl font-semibold text-[#00ff41] font-mono" style={{ textShadow: "0 0 6px #00ff4144" }}>{successRate > 0 ? `${(successRate * 100).toFixed(1)}%` : "—"}</div>
                <div className="text-xs text-zinc-500 mt-1">Success Rate</div>
              </div>
              <div>
                <div className="text-2xl font-semibold text-[#00ff41] font-mono" style={{ textShadow: "0 0 6px #00ff4144" }}>{avgMs > 0 ? `${(avgMs / 1000).toFixed(1)}s` : "—"}</div>
                <div className="text-xs text-zinc-500 mt-1">Avg Response</div>
              </div>
            </div>
            {successRate > 0 && (
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 bg-[#1a2e1a] rounded-full overflow-hidden">
                  <div className="h-full bg-[#00ff41] rounded-full transition-all" style={{ width: `${successRate * 100}%` }} />
                </div>
                <span className="text-xs text-zinc-500 font-mono">{(successRate * 100).toFixed(1)}%</span>
              </div>
            )}
          </div>
        )}

        {/* Reviews */}
        <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
          <h2 className="text-sm text-zinc-400 font-mono mb-4">// Reviews</h2>
          {ratings.length === 0 ? (
            <p className="text-zinc-500 text-sm font-mono">No reviews yet</p>
          ) : (
            <div className="space-y-4">
              {ratings.map(r => (
                <div key={r.id} className="border-b border-[#1a2e1a] pb-4 last:border-0 last:pb-0">
                  <div className="flex items-center gap-2">
                    <span className="text-yellow-400">{"★".repeat(Math.round(r.overall_score))}<span className="text-zinc-600">{"★".repeat(5 - Math.round(r.overall_score))}</span></span>
                    <span className="text-xs text-zinc-500">{timeAgo(r.created_at)}</span>
                  </div>
                  {r.feedback && <p className="text-sm text-zinc-300 mt-1">&ldquo;{r.feedback}&rdquo;</p>}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* External Agent Details */}
        {agent.is_external && (
          <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6 space-y-4">
            <h2 className="text-sm text-zinc-400 font-mono mb-4">// External Agent Details</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
              {agent.capabilities && (
                <div>
                  <span className="text-zinc-500">Capabilities: </span>
                  <span className="text-zinc-300">
                    streaming {agent.capabilities.streaming ? "✓" : "✗"} · push {agent.capabilities.push_notifications ? "✓" : "✗"}
                  </span>
                </div>
              )}
              {agent.provider_info?.name && (
                <div><span className="text-zinc-500">Provider: </span><span className="text-zinc-300">{agent.provider_info.name}</span></div>
              )}
              {agent.verification_status && (
                <div><span className="text-zinc-500">Verification: </span><span className={agent.verification_status === "verified" ? "text-emerald-400" : "text-yellow-400"}>{agent.verification_status}</span></div>
              )}
              {agent.last_health_check && (
                <div><span className="text-zinc-500">Last health check: </span><span className="text-zinc-300">{timeAgo(agent.last_health_check)}</span></div>
              )}
            </div>
            {agent.agent_card && (
              <details className="mt-3">
                <summary className="text-xs text-zinc-500 cursor-pointer hover:text-[#00ff41] transition-colors font-mono">▶ View Agent Card JSON</summary>
                <pre className="mt-2 bg-[#09090b] border border-[#1a2e1a] rounded-lg p-4 text-xs font-mono text-[#00ff41] overflow-x-auto max-h-64 overflow-y-auto">
                  {JSON.stringify(agent.agent_card, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}

        {/* Integration */}
        <div id="integration" className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
          <h2 className="text-sm text-zinc-400 font-mono mb-4">// Integration</h2>

          <div className="mb-4">
            <h3 className="text-xs text-zinc-500 font-mono mb-2">A2A Endpoint</h3>
            <pre className="bg-[#09090b] border border-[#1a2e1a] rounded-lg p-4 text-xs font-mono text-zinc-300 overflow-x-auto">
{`POST ${API_URL}/a2a/agents/${agent.slug}
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "message/send",
  "id": "1",
  "params": {
    "message": {
      "role": "user",
      "parts": [{"text": "Your request here"}]
    }
  }
}`}
            </pre>
          </div>

          <h3 className="text-xs text-zinc-500 font-mono mb-2">REST API</h3>
          <pre className="bg-[#09090b] border border-[#1a2e1a] rounded-lg p-4 text-xs font-mono text-zinc-300 overflow-x-auto">
{`curl -X POST ${API_URL}/v1/tasks \\
  -H "Authorization: Bearer YOUR_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "provider_agent_id": "${agent.id}",
    "skill_requested": "${selectedSkill || agent.skills?.[0]?.skill_tag || "skill"}",
    "payload": { "text": "Your input here" }
  }'`}
          </pre>
        </div>

        <div className="text-center">
          <Link href="/agents" className="text-sm text-zinc-500 hover:text-[#00ff41] transition-colors">← Back to marketplace</Link>
        </div>
      </div>
    </div>
  );
}
