"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "../../lib/auth-context";
import { getTasks } from "../../lib/api";
import { Button } from "../../lib/ui";
import { STATUS_DOT, timeAgo } from "../../lib/components";

type Task = {
  id: string; skill_requested: string; status: string; quoted_price: string;
  provider_agent_id?: string; created_at: string; description?: string;
};

const TABS = ["all", "requester", "provider"] as const;
const STATUSES = ["all", "pending", "assigned", "processing", "completed", "failed", "cancelled"];

function MyTasksContent() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [tab, setTab] = useState<string>("all");
  const [status, setStatus] = useState("all");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (tab !== "all") params.set("role", tab);
    if (status !== "all") params.set("status", status);
    getTasks(params.toString())
      .then(d => { setTasks(d.items || d.tasks || (Array.isArray(d) ? d : [])); })
      .catch(() => setTasks([]))
      .finally(() => setLoading(false));
  }, [tab, status]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-white">My Tasks</h1>
        <Link href="/tasks/new"><Button>Post Task</Button></Link>
      </div>
      <div className="flex items-center gap-6 mb-6">
        <div className="flex gap-1 bg-[#0a0f0a] rounded-lg p-1 border border-[#1a2e1a]">
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-md text-sm capitalize transition-colors font-mono ${tab === t ? "bg-[#0a1f0a] text-[#00ff41]" : "text-zinc-400 hover:text-[#00ff41]"}`}>
              {t === "all" ? "All" : `As ${t}`}
            </button>
          ))}
        </div>
        <select value={status} onChange={e => setStatus(e.target.value)}
          className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-lg px-3 py-1.5 text-sm text-[#00ff41] font-mono focus:outline-none focus:border-[#00ff41]">
          {STATUSES.map(s => <option key={s} value={s}>{s === "all" ? "All statuses" : s}</option>)}
        </select>
      </div>
      {loading ? <p className="text-zinc-500 font-mono">Loading...</p> : tasks.length === 0 ? (
        <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-8 text-center">
          <p className="text-zinc-400 mb-2">No tasks found</p>
          <p className="text-zinc-500 text-sm mb-4 font-mono">Post a task to an agent to get started</p>
          <Link href="/tasks/new"><Button>Post Task</Button></Link>
        </div>
      ) : (
        <div className="border border-[#1a2e1a] rounded-xl overflow-hidden bg-[#0a0f0a]">
          <div className="grid grid-cols-12 gap-2 px-5 py-3 border-b border-[#1a2e1a] text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
            <div className="col-span-3">Skill</div>
            <div className="col-span-2">Status</div>
            <div className="col-span-2 text-right">Price</div>
            <div className="col-span-3 text-right">Date</div>
            <div className="col-span-2 text-right">ID</div>
          </div>
          {tasks.map((t, i) => (
            <Link key={t.id} href={`/tasks/${t.id}`}
              className={`grid grid-cols-12 gap-2 px-5 py-3 items-center text-sm ${i < tasks.length - 1 ? "border-b border-[#1a2e1a]/50" : ""} hover:bg-[#0a1f0a]/30 transition-colors`}>
              <div className="col-span-3 text-[#00ff41] font-mono text-xs">{t.skill_requested || "—"}</div>
              <div className="col-span-2 flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${STATUS_DOT[t.status] || "bg-zinc-500"}`} />
                <span className="text-xs text-zinc-400 font-mono">{t.status}</span>
              </div>
              <div className="col-span-2 text-right text-xs text-zinc-400 font-mono">₹{parseFloat(t.quoted_price || "0").toFixed(2)}</div>
              <div className="col-span-3 text-right text-xs text-zinc-500 font-mono">{t.created_at ? timeAgo(t.created_at) : "—"}</div>
              <div className="col-span-2 text-right text-xs text-zinc-600 font-mono">{t.id?.slice(0, 8)}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DashboardTasksPage() {
  return <ProtectedRoute><MyTasksContent /></ProtectedRoute>;
}
