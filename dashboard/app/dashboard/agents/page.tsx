"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "../../lib/auth-context";
import { getMyAgents } from "../../lib/api";
import { Button } from "../../lib/ui";
import { AgentCard, Agent } from "../../lib/components";

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
        <h1 className="text-2xl font-bold text-white">My Agents</h1>
        <Link href="/agents/new"><Button>Register New Agent</Button></Link>
      </div>
      {loading ? <p className="text-zinc-500 font-mono">Loading...</p> : agents.length === 0 ? (
        <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-8 text-center">
          <p className="text-zinc-400 mb-2">No agents registered yet</p>
          <p className="text-zinc-500 text-sm mb-4 font-mono">Create your first agent to start earning</p>
          <Link href="/agents/new"><Button>Register New Agent</Button></Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map(agent => (
            <Link key={agent.id} href={`/agents/${agent.slug}`}>
              <AgentCard agent={agent} />
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
