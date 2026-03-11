"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "../lib/auth-context";
import { getMyAgents } from "../lib/api";
import { Card, StatusBadge, Button } from "../lib/ui";

interface Agent {
  id: string; name: string; slug: string; status: string;
  skills: string[]; price: number; rating: number; task_count: number;
  pricing_model: string;
}

function AgentsContent() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMyAgents()
      .then((d) => setAgents(Array.isArray(d) ? d : d.agents || []))
      .catch(() => setAgents([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Agents</h1>
        <Link href="/agents/new"><Button>Register New Agent</Button></Link>
      </div>
      {loading ? (
        <p className="text-zinc-500">Loading...</p>
      ) : agents.length === 0 ? (
        <Card><p className="text-zinc-500">No agents registered yet. Create your first one!</p></Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map((agent) => (
            <Link key={agent.id} href={`/agents/${agent.slug}`}>
              <Card className="hover:border-zinc-700 transition-colors cursor-pointer">
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-white">{agent.name}</h3>
                  <StatusBadge status={agent.status} />
                </div>
                <div className="flex flex-wrap gap-1.5 mb-3">
                  {(agent.skills || []).map((s) => (
                    <span key={s} className="px-2 py-0.5 bg-zinc-800 rounded text-xs text-zinc-300">{s}</span>
                  ))}
                </div>
                <div className="flex items-center gap-4 text-xs text-zinc-500">
                  <span>₹{agent.price}/{agent.pricing_model || "task"}</span>
                  <span>★ {agent.rating?.toFixed(1) || "—"}</span>
                  <span>{agent.task_count || 0} tasks</span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export default function AgentsPage() {
  return <ProtectedRoute><AgentsContent /></ProtectedRoute>;
}
