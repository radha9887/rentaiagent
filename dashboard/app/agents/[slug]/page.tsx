"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { getAgentPublic, getAgentRatingsPublic, API_URL, authFetch } from "../../lib/api";
import { Navbar, timeAgo, AgentIcon } from "../../lib/components";

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
  owner_id?: string;
  endpoint_url?: string;
  max_concurrent_tasks?: number;
  active_task_count?: number;
  health_status?: string;
  health_check_url?: string;
  health_avg_latency_ms?: number;
  health_last_checked_at?: string;
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
  const [agent, setAgent] = useState<AgentData | null>(null);
  const [ratings, setRatings] = useState<Rating[]>([]);
  const [loading, setLoading] = useState(true);
  const [isOwner, setIsOwner] = useState(false);

  // Owner edit state
  const [editDesc, setEditDesc] = useState("");
  const [editPrice, setEditPrice] = useState("");
  const [editEndpoint, setEditEndpoint] = useState("");
  const [editHealthUrl, setEditHealthUrl] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState("");
  const [toggling, setToggling] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    const hasJwt = !!localStorage.getItem("jwt");
    if (!slug) return;
    Promise.allSettled([
      getAgentPublic(slug as string),
      getAgentRatingsPublic(slug as string),
      ...(hasJwt ? [authFetch("/v1/agents/me").then(r => r.ok ? r.json() : null)] : []),
    ]).then(([a, r, myAgentsResult]) => {
      if (a.status === "fulfilled") {
        setAgent(a.value);
        setEditDesc(a.value.description || "");
        setEditPrice(a.value.price_per_task || "0");
        setEditEndpoint(a.value.endpoint_url || "");
        setEditHealthUrl(a.value.health_check_url || "");
      }
      if (r.status === "fulfilled") {
        const d = r.value;
        setRatings(d.items || (Array.isArray(d) ? d : []));
      }
      if (myAgentsResult && myAgentsResult.status === "fulfilled" && myAgentsResult.value) {
        const myAgents = myAgentsResult.value.agents || myAgentsResult.value.items || [];
        setIsOwner(myAgents.some((ma: { slug: string }) => ma.slug === slug));
      }
    }).finally(() => setLoading(false));
  }, [slug]);

  const price = parseFloat(agent?.price_per_task || "0");
  const tier = agent?.trust_tier?.toLowerCase() || "new";
  const avgMs = agent?.stats?.avg_response_ms || 0;
  const tasks = agent?.stats?.total_tasks || 0;
  const rating = agent?.stats?.avg_rating || 0;
  const ratingCount = agent?.stats?.rating_count || 0;
  const successRate = agent?.stats?.acceptance_rate || 0;
  const defaultSkill = agent?.skills?.[0]?.skill_tag || "skill";

  const handleSaveAgent = async () => {
    if (!agent) return;
    setSaving(true); setSaveMsg("");
    try {
      const body: Record<string, unknown> = {};
      if (editDesc !== (agent.description || "")) body.description = editDesc;
      if (editPrice !== (agent.price_per_task || "0")) body.price_per_task = parseFloat(editPrice) || 0;
      if (editEndpoint !== (agent.endpoint_url || "")) body.endpoint_url = editEndpoint;
      if (editHealthUrl !== (agent.health_check_url || "")) body.health_check_url = editHealthUrl;
      if (Object.keys(body).length === 0) { setSaveMsg("No changes"); setSaving(false); return; }
      const res = await authFetch(`/v1/agents/${agent.slug}`, { method: "PATCH", body: JSON.stringify(body) });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail || "Save failed"); }
      const updated = await res.json();
      setAgent(updated);
      setSaveMsg("Saved!");
      setTimeout(() => setSaveMsg(""), 3000);
    } catch (e: unknown) { setSaveMsg(e instanceof Error ? e.message : "Save failed"); }
    finally { setSaving(false); }
  };

  const handleToggleStatus = async () => {
    if (!agent) return;
    setToggling(true);
    try {
      const newStatus = agent.status === "online" ? "offline" : "online";
      const res = await authFetch(`/v1/agents/${agent.slug}`, { method: "PATCH", body: JSON.stringify({ status: newStatus }) });
      if (res.ok) { const updated = await res.json(); setAgent(updated); }
    } catch {} finally { setToggling(false); }
  };

  const handleDeleteAgent = async () => {
    if (!agent) return;
    setDeleting(true);
    try {
      const res = await authFetch(`/v1/agents/${agent.slug}`, { method: "DELETE" });
      if (res.ok) { router.push("/developers?tab=agents"); }
    } catch {} finally { setDeleting(false); }
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
        {/* Pending Verification Banner */}
        {agent.status === "pending_verification" && (
          <div className="border border-yellow-500/30 bg-yellow-500/5 rounded-xl p-4 flex items-center gap-3">
            <span className="text-xl">⏳</span>
            <p className="text-yellow-400 text-sm font-mono">This agent is pending verification. It will appear in the marketplace once the health endpoint is reachable.</p>
          </div>
        )}

        {/* Header */}
        <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6 md:p-8">
          <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
            <div className="space-y-2">
              <div className="flex items-center gap-3 flex-wrap">
                <AgentIcon size={24} />
                <h1 className="text-2xl md:text-3xl font-bold text-white">{agent.name}</h1>
                {agent.is_external && <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">External Agent 🌐</span>}
                <span className={`text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded border ${TIER_COLORS[tier] || TIER_COLORS.new}`}>{tier}</span>
                <span className={`inline-flex items-center gap-1.5 text-xs ${
                  agent.status === "online" || agent.status === "active" ? "text-emerald-400" :
                  agent.status === "pending_verification" ? "text-yellow-400" : "text-zinc-500"
                }`}>
                  <span className={`w-2 h-2 rounded-full ${
                    agent.status === "online" || agent.status === "active" ? "bg-emerald-400" :
                    agent.status === "pending_verification" ? "bg-yellow-400" : "bg-zinc-500"
                  }`} />
                  {agent.status === "pending_verification" ? "Pending Verification" : agent.status}
                </span>
              </div>
              <p className="text-sm text-zinc-500 font-mono">@{agent.slug}</p>
              {agent.description && <p className="text-sm text-zinc-400 max-w-2xl">{agent.description}</p>}
              <div className="flex flex-wrap items-center gap-3 text-sm text-zinc-400 pt-1">
                <span className="text-[#00ff41] font-semibold">{price}/task</span>
                {rating > 0 && <><span className="text-zinc-600">·</span><span><span className="text-yellow-400">★</span>{rating.toFixed(1)} ({ratingCount} reviews)</span></>}
                {avgMs > 0 && <><span className="text-zinc-600">·</span><span>⚡{(avgMs / 1000).toFixed(1)}s avg</span></>}
                <span className="text-zinc-600">·</span><span>{tasks.toLocaleString()} tasks</span>
              </div>
            </div>
          </div>
        </div>

        {/* Owner Controls */}
        {isOwner && (
          <div className="border border-[#00ff41]/20 bg-[#0a0f0a] rounded-xl p-6 space-y-5">
            <h2 className="text-sm text-[#00ff41] font-mono mb-2">// Owner Controls</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Description</label>
                <textarea value={editDesc} onChange={e => setEditDesc(e.target.value)} rows={2}
                  className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 resize-none" />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Price per task</label>
                  <input type="text" value={editPrice} onChange={e => setEditPrice(e.target.value)}
                    className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50" />
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Endpoint URL</label>
                  <input type="text" value={editEndpoint} onChange={e => setEditEndpoint(e.target.value)}
                    className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50" />
                </div>
                <div>
                  <label className="block text-sm text-zinc-400 mb-1">Health Check URL</label>
                  <input type="text" value={editHealthUrl} onChange={e => setEditHealthUrl(e.target.value)}
                    className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50" />
                </div>
              </div>
              <div className="flex items-center gap-3">
                <button onClick={handleSaveAgent} disabled={saving}
                  className="bg-[#00ff41] text-black font-semibold px-5 py-2 rounded-lg text-sm hover:bg-[#00ff41]/90 transition-colors disabled:opacity-50">
                  {saving ? "Saving..." : "Save Changes"}
                </button>
                {saveMsg && <span className="text-sm text-zinc-400 font-mono">{saveMsg}</span>}
              </div>
            </div>

            <div className="border-t border-[#1a2e1a] pt-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="text-sm text-zinc-400">Status:</span>
                <span className={`inline-flex items-center gap-1.5 text-sm font-mono ${agent.status === "online" ? "text-emerald-400" : agent.status === "pending_verification" ? "text-yellow-400" : "text-zinc-500"}`}>
                  <span className={`w-2 h-2 rounded-full ${agent.status === "online" ? "bg-emerald-400" : agent.status === "pending_verification" ? "bg-yellow-400" : "bg-zinc-500"}`} />
                  {agent.status === "pending_verification" ? "Pending Verification" : agent.status}
                </span>
                <button onClick={handleToggleStatus} disabled={toggling}
                  className="text-xs px-3 py-1.5 rounded border border-[#1a2e1a] text-zinc-300 hover:border-[#00ff4155] hover:text-[#00ff41] transition-colors font-mono disabled:opacity-50">
                  {toggling ? "..." : agent.status === "online" ? "Go Offline" : "Go Online"}
                </button>
              </div>
              <div>
                {!showDeleteConfirm ? (
                  <button onClick={() => setShowDeleteConfirm(true)}
                    className="text-xs px-3 py-1.5 rounded border border-red-500/30 text-red-400 hover:bg-red-500/10 transition-colors font-mono">
                    Delete Agent
                  </button>
                ) : (
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-red-400 font-mono">Are you sure?</span>
                    <button onClick={handleDeleteAgent} disabled={deleting}
                      className="text-xs px-3 py-1.5 rounded bg-red-500/20 border border-red-500/30 text-red-400 hover:bg-red-500/30 transition-colors font-mono disabled:opacity-50">
                      {deleting ? "Deleting..." : "Yes, Delete"}
                    </button>
                    <button onClick={() => setShowDeleteConfirm(false)}
                      className="text-xs px-3 py-1.5 rounded border border-[#1a2e1a] text-zinc-400 hover:text-zinc-300 transition-colors font-mono">
                      Cancel
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

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

        {/* Health & Capacity */}
        <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
          <h2 className="text-sm text-zinc-400 font-mono mb-4">// Health & Capacity</h2>
          <div className="grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="flex items-center justify-center gap-2">
                <span className={`w-2.5 h-2.5 rounded-full ${agent.health_status === "healthy" ? "bg-emerald-400" : agent.health_status === "unhealthy" ? "bg-red-400" : "bg-zinc-500"}`} />
                <span className={`text-lg font-semibold font-mono ${agent.health_status === "healthy" ? "text-emerald-400" : agent.health_status === "unhealthy" ? "text-red-400" : "text-zinc-500"}`}>
                  {agent.health_status === "healthy" ? `Healthy${agent.health_avg_latency_ms ? ` (${Math.round(agent.health_avg_latency_ms)}ms)` : ""}` : agent.health_status === "unhealthy" ? "Unhealthy" : "Unknown"}
                </span>
              </div>
              <div className="text-xs text-zinc-500 mt-1">Health</div>
            </div>
            <div>
              <div className="text-2xl font-semibold text-[#00ff41] font-mono" style={{ textShadow: "0 0 6px #00ff4144" }}>
                {agent.active_task_count ?? 0}/{agent.max_concurrent_tasks ?? 10}
              </div>
              <div className="text-xs text-zinc-500 mt-1">Slots Used</div>
            </div>
            <div>
              <div className="text-sm font-mono text-zinc-400">
                {agent.health_last_checked_at ? timeAgo(agent.health_last_checked_at) : "Never"}
              </div>
              <div className="text-xs text-zinc-500 mt-1">Last Checked</div>
            </div>
          </div>
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

        
        <div className="text-center">
          <Link href="/agents" className="text-sm text-zinc-500 hover:text-[#00ff41] transition-colors">← Back to marketplace</Link>
        </div>
      </div>
    </div>
  );
}
