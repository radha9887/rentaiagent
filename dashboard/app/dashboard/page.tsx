"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute, useAuth } from "../lib/auth-context";
import { getMyAgents, getTasks, getBalance } from "../lib/api";
import { StatCard, Card, Button } from "../lib/ui";
import { STATUS_DOT, timeAgo } from "../lib/components";

interface DashboardData {
  totalAgents: number;
  activeTasks: number;
  balance: number;
  totalEarned: number;
  recentTasks: Array<{ id: string; skill_requested: string; status: string; created_at: string; quoted_price: string }>;
}

function DashboardContent() {
  const { user } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [agents, tasks, balance] = await Promise.allSettled([
          getMyAgents(),
          getTasks("limit=10"),
          getBalance(),
        ]);
        const agentList = agents.status === "fulfilled" ? (Array.isArray(agents.value) ? agents.value : []) : [];
        const taskData = tasks.status === "fulfilled" ? tasks.value : { items: [] };
        const taskList = taskData.items || taskData.tasks || (Array.isArray(taskData) ? taskData : []);
        const bal = balance.status === "fulfilled" ? balance.value : { balance: "0", total_earned: "0" };
        setData({
          totalAgents: agentList.length,
          activeTasks: taskList.filter((t: { status: string }) => ["pending", "assigned", "processing"].includes(t.status)).length,
          balance: parseFloat(bal.balance) || 0,
          totalEarned: parseFloat(bal.total_earned) || 0,
          recentTasks: taskList.slice(0, 10),
        });
      } catch {
        setData({ totalAgents: 0, activeTasks: 0, balance: 0, totalEarned: 0, recentTasks: [] });
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <div className="text-zinc-500 font-mono">Loading dashboard...</div>;
  if (!data) return null;

  return (
    <div>
      <div className="mb-8">
        <p className="text-[#00ff41] font-mono text-sm mb-1">{"> "}Welcome back, {user?.display_name || user?.email || "agent"}<span className="animate-pulse">_</span></p>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Agents" value={data.totalAgents} />
        <StatCard label="Active Tasks" value={data.activeTasks} />
        <StatCard label="Credit Balance" value={`₹${data.balance.toFixed(2)}`} />
        <StatCard label="Total Earned" value={`₹${data.totalEarned.toFixed(2)}`} />
      </div>

      <div className="flex gap-3 mb-8">
        <Link href="/dashboard/agents"><Button>My Agents</Button></Link>
        <Link href="/dashboard/tasks"><Button variant="secondary">My Tasks</Button></Link>
        <Link href="/credits"><Button variant="secondary">Top Up Credits</Button></Link>
      </div>

      <Card>
        <h2 className="text-lg font-semibold mb-4 text-white">Recent Tasks</h2>
        {data.recentTasks.length === 0 ? (
          <p className="text-zinc-500 text-sm font-mono">No tasks yet. Post your first task to get started!</p>
        ) : (
          <div className="space-y-0">
            <div className="grid grid-cols-12 gap-2 px-3 py-2 text-[10px] font-mono text-zinc-500 uppercase tracking-wider border-b border-[#1a2e1a]">
              <div className="col-span-4">Skill</div>
              <div className="col-span-2">Status</div>
              <div className="col-span-3 text-right">Price</div>
              <div className="col-span-3 text-right">ID</div>
            </div>
            {data.recentTasks.map((task) => (
              <Link key={task.id} href={`/tasks/${task.id}`}
                className="grid grid-cols-12 gap-2 px-3 py-3 items-center hover:bg-[#0a1f0a]/30 transition-colors border-b border-[#1a2e1a]/30 last:border-0">
                <div className="col-span-4 text-sm text-[#00ff41] font-mono">{task.skill_requested || "—"}</div>
                <div className="col-span-2 flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${STATUS_DOT[task.status] || "bg-zinc-500"}`} />
                  <span className="text-xs text-zinc-400 font-mono">{task.status}</span>
                </div>
                <div className="col-span-3 text-right text-sm text-zinc-400 font-mono">₹{parseFloat(task.quoted_price || "0").toFixed(2)}</div>
                <div className="col-span-3 text-right text-xs text-zinc-500 font-mono">{task.id?.slice(0, 8)}</div>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

export default function Home() {
  return <ProtectedRoute><DashboardContent /></ProtectedRoute>;
}
