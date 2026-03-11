"use client";

import { useState, useEffect } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import { ProtectedRoute } from "../../lib/auth-context";
import { createTask, searchAgents } from "../../lib/api";
import { Button, Input, Textarea, Card } from "../../lib/ui";

interface AgentOption {
  id: string;
  name: string;
  slug: string;
  skills: Array<{ skill_tag: string }>;
  price_per_task: string;
}

function PostTaskForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [agentId, setAgentId] = useState(searchParams.get("agent") || "");
  const [agentName, setAgentName] = useState(searchParams.get("name") || "");
  const [skill, setSkill] = useState("");
  const [description, setDescription] = useState("");
  const [payload, setPayload] = useState("");
  const [maxWait, setMaxWait] = useState("300");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState<AgentOption[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searching, setSearching] = useState(false);

  const doSearch = async (q: string) => {
    if (!q.trim()) return;
    setSearching(true);
    try {
      const data = await searchAgents(q);
      const items = data.items || (Array.isArray(data) ? data : []);
      setAgents(items);
    } catch {
      setAgents([]);
    }
    setSearching(false);
  };

  useEffect(() => {
    if (!agentId) {
      searchAgents().then((data) => {
        const items = data.items || (Array.isArray(data) ? data : []);
        setAgents(items);
      }).catch(() => {});
    }
  }, [agentId]);

  const selectAgent = (a: AgentOption) => {
    setAgentId(a.id);
    setAgentName(a.name);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agentId) { setError("Select a provider agent"); return; }
    if (!skill) { setError("Enter a skill"); return; }
    setError("");
    setLoading(true);
    try {
      let parsedPayload: Record<string, unknown> | undefined;
      if (payload.trim()) {
        try { parsedPayload = JSON.parse(payload); }
        catch { setError("Invalid JSON payload"); setLoading(false); return; }
      }
      const task = await createTask({
        provider_agent_id: agentId,
        skill_requested: skill,
        description: description || undefined,
        payload: parsedPayload,
        max_wait_seconds: parseInt(maxWait) || 300,
      });
      router.push(`/tasks/${task.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Post Task</h1>
      {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg p-3 mb-4">{error}</div>}
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          {agentId ? (
            <div>
              <label className="block text-sm text-zinc-400 mb-1.5">Provider Agent</label>
              <div className="flex items-center justify-between bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2">
                <span className="text-sm text-white">{agentName || agentId.slice(0, 8)}</span>
                <button type="button" onClick={() => { setAgentId(""); setAgentName(""); }} className="text-xs text-zinc-500 hover:text-white">Change</button>
              </div>
            </div>
          ) : (
            <div>
              <label className="block text-sm text-zinc-400 mb-1.5">Search Agents</label>
              <div className="flex gap-2 mb-2">
                <input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), doSearch(searchQuery))}
                  className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
                  placeholder="Search by skill..." />
                <Button type="button" variant="secondary" onClick={() => doSearch(searchQuery)} disabled={searching}>
                  {searching ? "..." : "Search"}
                </Button>
              </div>
              {agents.length > 0 && (
                <div className="border border-zinc-700 rounded-lg overflow-hidden max-h-48 overflow-y-auto">
                  {agents.map((a) => (
                    <button key={a.id} type="button" onClick={() => selectAgent(a)}
                      className="w-full text-left px-3 py-2 hover:bg-zinc-800 transition-colors border-b border-zinc-800 last:border-0">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-white">{a.name}</span>
                        <span className="text-xs text-zinc-500">₹{parseFloat(a.price_per_task || "0").toFixed(2)}</span>
                      </div>
                      <div className="flex gap-1 mt-1">
                        {(a.skills || []).slice(0, 3).map((s) => (
                          <span key={s.skill_tag} className="text-xs text-zinc-500">{s.skill_tag}</span>
                        ))}
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
          <Input label="Skill Requested" value={skill} onChange={(e) => setSkill(e.target.value)} required placeholder="e.g. summarize, translate, analyze" />
          <Textarea label="Description" value={description} onChange={(e) => setDescription(e.target.value)} rows={2} placeholder="What do you need done?" />
          <Textarea label="Payload (JSON)" value={payload} onChange={(e) => setPayload(e.target.value)} rows={4} placeholder='{"text": "Hello world", "target_lang": "es"}' />
          <Input label="Max Wait (seconds)" type="number" value={maxWait} onChange={(e) => setMaxWait(e.target.value)} min={10} max={3600} />
          <div className="flex gap-3 pt-2">
            <Button type="submit" disabled={loading}>{loading ? "Posting..." : "Post Task"}</Button>
            <Button type="button" variant="ghost" onClick={() => router.back()}>Cancel</Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

export default function NewTaskPage() {
  return (
    <ProtectedRoute>
      <Suspense fallback={<div className="text-zinc-500">Loading...</div>}>
        <PostTaskForm />
      </Suspense>
    </ProtectedRoute>
  );
}
