"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "../lib/auth-context";
import { getMyAgents, getTasks, getBalance } from "../lib/api";
import { StatCard, Card, StatusBadge, Button } from "../lib/ui";

interface DashboardData {
  totalAgents: number;
  activeTasks: number;
  balance: number;
  totalEarned: number;
  recentTasks: Array<{ id: string; skill_requested: string; status: string; created_at: string; quoted_price: string }>;
}

function DashboardContent() {
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

  if (loading) return <div className="text-zinc-500">Loading dashboard...</div>;
  if (!data) return null;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Agents" value={data.totalAgents} />
        <StatCard label="Active Tasks" value={data.activeTasks} />
        <StatCard label="Credit Balance" value={`₹${data.balance.toFixed(2)}`} />
        <StatCard label="Total Earned" value={`₹${data.totalEarned.toFixed(2)}`} />
      </div>

      <div className="flex gap-3 mb-8">
        <Link href="/agents/new"><Button>Register Agent</Button></Link>
        <Link href="/tasks/new"><Button variant="secondary">Post Task</Button></Link>
        <Link href="/credits"><Button variant="secondary">Top Up Credits</Button></Link>
      </div>

      <Card>
        <h2 className="text-lg font-semibold mb-4">Recent Tasks</h2>
        {data.recentTasks.length === 0 ? (
          <p className="text-zinc-500 text-sm">No tasks yet. Post your first task to get started!</p>
        ) : (
          <div className="space-y-2">
            {data.recentTasks.map((task) => (
              <Link key={task.id} href={`/tasks/${task.id}`} className="flex items-center justify-between p-3 rounded-lg hover:bg-zinc-800/50 transition-colors">
                <div className="flex items-center gap-3">
                  <span className="text-sm text-white">{task.skill_requested || "—"}</span>
                  <StatusBadge status={task.status} />
                </div>
                <div className="flex items-center gap-4">
                  <span className="text-sm text-zinc-400">₹{parseFloat(task.quoted_price || "0").toFixed(2)}</span>
                  <span className="text-xs text-zinc-500 font-mono">{task.id?.slice(0, 8)}</span>
                </div>
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
