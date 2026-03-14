"use client";

import { useEffect, useState } from "react";
import { API_URL } from "../lib/api";
import { FeedTask, STATUS_DOT, timeAgo, Navbar } from "../lib/components";

const STATUSES = ["all", "completed", "pending", "processing", "failed", "cancelled", "escrowed"];
const PAGE_SIZE = 20;

export default function TransactionExplorer() {
  const [tasks, setTasks] = useState<FeedTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("all");
  const [skillFilter, setSkillFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

  function fetchTasks(newOffset: number) {
    setLoading(true);
    const params = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(newOffset) });
    if (statusFilter !== "all") params.set("status", statusFilter);
    if (skillFilter) params.set("skill", skillFilter);
    fetch(`${API_URL}/v1/tasks/feed?${params}`)
      .then(r => r.json())
      .then(d => {
        setTasks(d.tasks || []);
        setTotal(d.total || 0);
        setOffset(newOffset);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchTasks(0);
  }, [statusFilter, skillFilter]);

  const showingFrom = total === 0 ? 0 : offset + 1;
  const showingTo = Math.min(offset + PAGE_SIZE, total);

  return (
    <div className="bg-[#09090b] min-h-screen">
      <Navbar />

      <div className="max-w-6xl mx-auto px-6 pt-24 pb-16">
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">Transaction Explorer</h1>
          <p className="text-zinc-400">Every task is public. Full transparency.</p>
        </div>

        <div className="flex flex-wrap items-center gap-3 mb-6 justify-center">
          <input
            type="text" placeholder="> filter by skill..." value={skillFilter} onChange={e => { setSkillFilter(e.target.value); }}
            className="bg-[#0a0f0a] border border-[#1a2e1a] text-[#00ff41] font-mono text-sm rounded-lg px-4 py-2 focus:outline-none focus:border-[#00ff41] placeholder-zinc-600 w-64"
          />
          <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
            className="bg-[#0a0f0a] border border-[#1a2e1a] text-[#00ff41] font-mono text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-[#00ff41]">
            {STATUSES.map(s => <option key={s} value={s}>{s === "all" ? "All statuses" : s}</option>)}
          </select>
        </div>

        {loading ? (
          <p className="text-zinc-500 text-center py-12 font-mono">Loading transactions...</p>
        ) : (
          <div className="border border-[#1a2e1a] rounded-xl overflow-hidden bg-[#0a0f0a]">
            <div className="grid grid-cols-12 gap-2 px-5 py-3 border-b border-[#1a2e1a] text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
              <div className="col-span-2">Status</div><div className="col-span-3">Skill</div><div className="col-span-3">Agent</div>
              <div className="col-span-1 text-right">Cost</div><div className="col-span-1 text-right">Time</div><div className="col-span-2 text-right">When</div>
            </div>
            {tasks.length === 0 ? (
              <div className="px-5 py-12 text-center text-zinc-500 font-mono text-sm">No transactions found.</div>
            ) : tasks.map((t, i) => (
              <div key={t.id} className={`grid grid-cols-12 gap-2 px-5 py-3 items-center text-sm ${i < tasks.length - 1 ? "border-b border-[#1a2e1a]/50" : ""} hover:bg-[#0a1f0a]/30 transition-colors`}>
                <div className="col-span-2 flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${STATUS_DOT[t.status] || "bg-zinc-500"}`} />
                  <span className="text-xs text-zinc-400 font-mono">{t.status}</span>
                </div>
                <div className="col-span-3"><span className="text-xs text-[#00ff41] font-mono">{t.skill}</span></div>
                <div className="col-span-3"><span className="text-xs text-zinc-300">{t.agent_name}</span></div>
                <div className="col-span-1 text-right"><span className="text-xs text-zinc-400 font-mono">{parseFloat(t.price).toFixed(0)} credits</span></div>
                <div className="col-span-1 text-right"><span className="text-xs text-zinc-500 font-mono">{t.duration_s ? `${t.duration_s}s` : "—"}</span></div>
                <div className="col-span-2 text-right"><span className="text-xs text-zinc-600 font-mono">{t.created_at ? timeAgo(t.created_at) : "—"}</span></div>
              </div>
            ))}
          </div>
        )}

        {/* Pagination */}
        <div className="flex items-center justify-between mt-4 font-mono text-xs">
          <p className="text-zinc-500">
            {total > 0 ? `Showing ${showingFrom}–${showingTo} of ${total} transactions` : "No transactions"}
          </p>
          <div className="flex gap-2">
            <button
              onClick={() => fetchTasks(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0}
              className="px-4 py-2 border border-[#1a2e1a] rounded-lg text-[#00ff41] hover:bg-[#0a1f0a] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              ← Previous
            </button>
            <button
              onClick={() => fetchTasks(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= total}
              className="px-4 py-2 border border-[#1a2e1a] rounded-lg text-[#00ff41] hover:bg-[#0a1f0a] transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              Next →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
