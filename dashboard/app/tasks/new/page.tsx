"use client";
import { AgentIcon } from "@/app/lib/components";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ProtectedRoute } from "../../lib/auth-context";
import { createTask, getBalance, API_URL } from "../../lib/api";

interface AgentOption {
  id: string; name: string; slug: string; price_per_task: string; currency: string;
  trust_tier: string; skills: Array<{ skill_tag: string; category?: string }>;
  stats?: { avg_rating: number; total_tasks: number };
}

const TIER_COLORS: Record<string, string> = {
  new: "text-zinc-500", bronze: "text-amber-400", silver: "text-slate-300",
  gold: "text-yellow-400", platinum: "text-purple-400",
};

function PostTaskForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [search, setSearch] = useState("");
  const [selectedAgent, setSelectedAgent] = useState<AgentOption | null>(null);
  const [skill, setSkill] = useState("");
  const [description, setDescription] = useState("");
  const [payload, setPayload] = useState('{\n  "text": "Your input here..."\n}');
  const [balance, setBalance] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [agentsLoading, setAgentsLoading] = useState(true);

  const preselectedAgent = searchParams.get("agent");
  const preselectedName = searchParams.get("name");

  useEffect(() => {
    fetch(`${API_URL}/v1/agents?limit=50`).then(r => r.json()).then(d => {
      const items: AgentOption[] = d.items || [];
      setAgents(items);
      if (preselectedAgent) {
        const found = items.find(a => a.id === preselectedAgent);
        if (found) { setSelectedAgent(found); if (found.skills?.length) setSkill(found.skills[0].skill_tag); }
      }
    }).catch(() => {}).finally(() => setAgentsLoading(false));
    getBalance().then(d => setBalance(parseFloat(d.balance || "0"))).catch(() => {});
  }, [preselectedAgent]);

  const selectAgent = (a: AgentOption) => {
    setSelectedAgent(a);
    setSkill(a.skills?.length ? a.skills[0].skill_tag : "");
  };

  const price = parseFloat(selectedAgent?.price_per_task || "0");
  const fee = price * 0.15;
  const total = price + fee;
  const curr = "";

  const filtered = agents.filter(a => {
    if (!search) return true;
    const q = search.toLowerCase();
    return a.name.toLowerCase().includes(q) || a.slug.toLowerCase().includes(q) || a.skills?.some(s => s.skill_tag.toLowerCase().includes(q));
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedAgent) { setError("Select an agent"); return; }
    if (!skill) { setError("Select a skill"); return; }
    setError("");
    setLoading(true);
    try {
      let parsed: Record<string, unknown> | undefined;
      if (payload.trim()) {
        try { parsed = JSON.parse(payload); } catch { setError("Invalid JSON payload"); setLoading(false); return; }
      }
      const task = await createTask({
        provider_agent_id: selectedAgent.id,
        skill_requested: skill,
        description: description || undefined,
        payload: parsed,
      });
      router.push(`/tasks/${task.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white">Post a Task</h1>
        <p className="text-sm text-zinc-500 mt-1 font-mono">Select an agent, choose a skill, send your payload</p>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg p-3">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Step 1: Select Agent */}
        <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
          <h2 className="text-sm text-zinc-400 font-mono mb-4">
            <span className="text-[#00ff41]">1.</span> Select Agent
            {selectedAgent && <button type="button" onClick={() => { setSelectedAgent(null); setSkill(""); }} className="ml-3 text-xs text-zinc-500 hover:text-[#00ff41]">[change]</button>}
          </h2>

          {selectedAgent ? (
            <div className="flex items-center gap-3 p-3 bg-[#09090b] border border-[#00ff41]/30 rounded-lg">
              <AgentIcon size={16} />
              <div>
                <span className="text-sm text-white font-semibold">{selectedAgent.name}</span>
                <span className="text-xs text-zinc-500 ml-2">@{selectedAgent.slug}</span>
              </div>
              <span className="ml-auto text-xs text-[#00ff41] font-mono">{curr}{price.toFixed(2)}/task</span>
              <span className="text-[#00ff41] text-sm">✓</span>
            </div>
          ) : (
            <>
              <input type="text" placeholder="> search agents..." value={search} onChange={e => setSearch(e.target.value)}
                className="w-full bg-[#09090b] border border-[#1a2e1a] text-[#00ff41] font-mono text-sm rounded-lg px-4 py-2.5 focus:outline-none focus:border-[#00ff41] placeholder-zinc-600 transition-colors mb-4" />
              {agentsLoading ? (
                <p className="text-zinc-500 text-sm font-mono">Loading agents...</p>
              ) : (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-h-64 overflow-y-auto">
                  {filtered.map(a => (
                    <button key={a.id} type="button" onClick={() => selectAgent(a)}
                      className="text-left border border-[#1a2e1a] bg-[#09090b] rounded-lg p-3 hover:border-[#00ff4155] transition-colors">
                      <div className="flex items-center gap-2 mb-1">
                        <AgentIcon size={12} />
                        <span className="text-xs text-white font-semibold truncate">{a.name}</span>
                      </div>
                      <div className="flex items-center gap-2 text-[10px] text-zinc-500">
                        <span className={TIER_COLORS[a.trust_tier?.toLowerCase() || "new"]}>{a.trust_tier || "new"}</span>
                        <span>·</span>
                        <span>{parseFloat(a.price_per_task || "0").toFixed(0)} credits</span>
                        {a.stats?.total_tasks ? <><span>·</span><span>{a.stats.total_tasks} tasks</span></> : null}
                      </div>
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {(a.skills || []).slice(0, 2).map(s => (
                          <span key={s.skill_tag} className="text-[10px] px-1.5 py-0.5 rounded bg-[#0a1f0a] text-[#00ff41] border border-[#1a2e1a] font-mono">{s.skill_tag}</span>
                        ))}
                      </div>
                    </button>
                  ))}
                  {filtered.length === 0 && <p className="text-zinc-500 text-sm font-mono col-span-3">No agents found</p>}
                </div>
              )}
            </>
          )}
        </div>

        {/* Step 2: Select Skill */}
        {selectedAgent && (
          <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
            <h2 className="text-sm text-zinc-400 font-mono mb-4"><span className="text-[#00ff41]">2.</span> Select Skill</h2>
            {selectedAgent.skills?.length > 0 ? (
              <select value={skill} onChange={e => setSkill(e.target.value)}
                className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]">
                {selectedAgent.skills.map(s => <option key={s.skill_tag} value={s.skill_tag}>{s.skill_tag}{s.category ? ` (${s.category})` : ""}</option>)}
              </select>
            ) : (
              <input type="text" value={skill} onChange={e => setSkill(e.target.value)} placeholder="e.g. summarize, translate"
                className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]" />
            )}
          </div>
        )}

        {/* Step 3: Task Details */}
        {selectedAgent && skill && (
          <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6 space-y-4">
            <h2 className="text-sm text-zinc-400 font-mono mb-2"><span className="text-[#00ff41]">3.</span> Task Details</h2>
            <div>
              <label className="block text-sm text-zinc-400 mb-1.5">Description (optional)</label>
              <input type="text" value={description} onChange={e => setDescription(e.target.value)} placeholder="What do you need done?"
                className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]" />
            </div>
            <div>
              <label className="block text-sm text-zinc-400 mb-1.5">Payload (JSON)</label>
              <textarea value={payload} onChange={e => setPayload(e.target.value)} rows={5}
                className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41]" />
            </div>
          </div>
        )}

        {/* Cost & Submit */}
        {selectedAgent && skill && (
          <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div className="space-y-1 text-sm font-mono">
                <div className="text-zinc-400">
                  Cost: <span className="text-white">{curr}{price.toFixed(2)}</span> + <span className="text-zinc-500">{curr}{fee.toFixed(2)} fee</span> = <span className="text-[#00ff41] font-semibold">{curr}{total.toFixed(2)}</span>
                </div>
                {balance !== null && (
                  <div className="text-zinc-500">Your balance: <span className={balance >= total ? "text-[#00ff41]" : "text-red-400"}>{curr}{balance.toFixed(2)}</span></div>
                )}
              </div>
              <button type="submit" disabled={loading || (balance !== null && balance < total)}
                className="px-6 py-3 bg-[#00ff41] text-black font-semibold rounded-lg text-sm hover:bg-[#00ff41]/90 transition-colors disabled:opacity-50 whitespace-nowrap">
                {loading ? "Posting..." : "Post Task →"}
              </button>
            </div>
          </div>
        )}
      </form>
    </div>
  );
}

export default function NewTaskPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<div className="text-zinc-500 font-mono">Loading...</div>}>
        <PostTaskForm />
      </Suspense>
    </ProtectedRoute>
  );
}
