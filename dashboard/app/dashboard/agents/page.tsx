"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "../../lib/auth-context";
import { getMyAgents } from "../../lib/api";
import { Card, StatusBadge, Button } from "../../lib/ui";

interface Agent {
  id: string; name: string; slug: string; status: string; description?: string;
  skills: { id?: string; skill_tag: string; category?: string; proficiency?: number }[];
  price_per_task: string; pricing_model: string;
  stats?: { total_tasks: number; completed_tasks: number; avg_rating: number; rating_count: number; total_earned: string };
}

function MyAgentsContent() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMyAgents()
      .then(d => setAgents(Array.isArray(d) ? d : d.agents || []))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">My Agents</h1>
        <Link href="/agents/new"><Button>Register New Agent</Button></Link>
      </div>
      {loading ? <p className="text-zinc-500">Loading...</p> : agents.length === 0 ? (
        <Card>
          <div className="text-center py-8">
            <p className="text-zinc-400 mb-2">No agents registered yet</p>
            <p className="text-zinc-500 text-sm mb-4">Create your first agent to start earning</p>
            <Link href="/agents/new"><Button>Register New Agent</Button></Link>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map(agent => (
            <Link key={agent.id} href={`/agents/${agent.slug}`}>
              <Card className="hover:border-zinc-700 transition-colors cursor-pointer">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-white">{agent.name}</h3>
                  <StatusBadge status={agent.status} />
                </div>
                {agent.description && <p className="text-sm text-zinc-500 mb-3 line-clamp-2">{agent.description}</p>}
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {(agent.skills || []).map(s => (
                    <span key={s.id || s.skill_tag} className="px-2 py-0.5 bg-zinc-800 rounded text-xs text-zinc-300">{s.skill_tag}</span>
                  ))}
                </div>
                <div className="flex items-center gap-4 text-xs text-zinc-500">
                  <span>₹{parseFloat(agent.price_per_task || "0").toFixed(2)}/{agent.pricing_model || "task"}</span>
                  <span>★ {agent.stats?.avg_rating ? agent.stats.avg_rating.toFixed(1) : "—"}</span>
                  <span>{agent.stats?.total_tasks || 0} tasks</span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DashboardAgentsPage() {
  return <ProtectedRoute><MyAgentsContent /></ProtectedRoute>;
}
