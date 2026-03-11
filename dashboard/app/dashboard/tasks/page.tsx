"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "../../lib/auth-context";
import { getTasks } from "../../lib/api";
import { Card, StatusBadge, Button } from "../../lib/ui";

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
        <h1 className="text-2xl font-bold">My Tasks</h1>
        <Link href="/tasks/new"><Button>Post Task</Button></Link>
      </div>
      <div className="flex items-center gap-6 mb-6">
        <div className="flex gap-1 bg-zinc-900 rounded-lg p-1 border border-zinc-800">
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-3 py-1.5 rounded-md text-sm capitalize transition-colors ${tab === t ? "bg-zinc-800 text-white" : "text-zinc-400 hover:text-white"}`}>
              {t === "all" ? "All" : `As ${t}`}
            </button>
          ))}
        </div>
        <select value={status} onChange={e => setStatus(e.target.value)}
          className="bg-zinc-900 border border-zinc-800 rounded-lg px-3 py-1.5 text-sm text-white">
          {STATUSES.map(s => <option key={s} value={s}>{s === "all" ? "All statuses" : s}</option>)}
        </select>
      </div>
      {loading ? <p className="text-zinc-500">Loading...</p> : tasks.length === 0 ? (
        <Card>
          <div className="text-center py-8">
            <p className="text-zinc-400 mb-2">No tasks found</p>
            <p className="text-zinc-500 text-sm mb-4">Post a task to an agent to get started</p>
            <Link href="/tasks/new"><Button>Post Task</Button></Link>
          </div>
        </Card>
      ) : (
        <Card className="!p-0 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-zinc-800 text-left text-xs text-zinc-500">
                <th className="px-4 py-3">Skill</th><th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Price</th><th className="px-4 py-3">Date</th><th className="px-4 py-3">ID</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map(t => (
                <tr key={t.id} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                  <td className="px-4 py-3"><Link href={`/tasks/${t.id}`} className="text-sm text-white hover:underline">{t.skill_requested || "—"}</Link></td>
                  <td className="px-4 py-3"><StatusBadge status={t.status} /></td>
                  <td className="px-4 py-3 text-sm text-zinc-300">₹{parseFloat(t.quoted_price || "0").toFixed(2)}</td>
                  <td className="px-4 py-3 text-xs text-zinc-500">{new Date(t.created_at).toLocaleDateString()}</td>
                  <td className="px-4 py-3 text-xs text-zinc-500 font-mono">{t.id?.slice(0, 8)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

export default function DashboardTasksPage() {
  return <ProtectedRoute><MyTasksContent /></ProtectedRoute>;
}
