"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ProtectedRoute } from "../../lib/auth-context";
import { getAgent } from "../../lib/api";
import { Card, StatCard, StatusBadge } from "../../lib/ui";

function AgentDetailContent() {
  const { slug } = useParams();
  const [agent, setAgent] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (slug) getAgent(slug as string).then(setAgent).catch(() => null).finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <p className="text-zinc-500">Loading...</p>;
  if (!agent) return <p className="text-zinc-400">Agent not found</p>;

  const tasks = (agent.recent_tasks || agent.tasks || []) as Array<{ id: string; skill: string; status: string; price: number }>;
  const ratings = (agent.ratings || []) as Array<{ rating: number; comment: string; created_at: string }>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{agent.name as string}</h1>
            <StatusBadge status={agent.status as string} />
          </div>
          <p className="text-sm text-zinc-500 font-mono mt-1">{agent.slug as string}</p>
        </div>
        <Link href={`/agents/${slug}/edit`} className="px-4 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-sm hover:bg-zinc-700 transition-colors">
          Edit
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Tasks" value={(agent.task_count as number) || 0} />
        <StatCard label="Rating" value={`★ ${(agent.rating as number)?.toFixed(1) || "—"}`} />
        <StatCard label="Price" value={`₹${agent.price}`} sub={agent.pricing_model as string} />
        <StatCard label="Protocol" value={(agent.protocols as string[])?.[0] || "a2a"} />
      </div>

      <Card className="mb-6">
        <h2 className="text-sm text-zinc-400 mb-2">Description</h2>
        <p className="text-white">{(agent.description as string) || "No description"}</p>
        <h2 className="text-sm text-zinc-400 mt-4 mb-2">Endpoint</h2>
        <code className="text-sm font-mono text-zinc-300">{agent.endpoint_url as string}</code>
        <h2 className="text-sm text-zinc-400 mt-4 mb-2">Skills</h2>
        <div className="flex flex-wrap gap-1.5">
          {((agent.skills as string[]) || []).map((s) => (
            <span key={s} className="px-2 py-0.5 bg-zinc-800 rounded text-xs text-zinc-300">{s}</span>
          ))}
        </div>
      </Card>

      <Card className="mb-6">
        <h2 className="text-lg font-semibold mb-3">Recent Tasks</h2>
        {tasks.length === 0 ? <p className="text-zinc-500 text-sm">No tasks</p> : (
          <div className="space-y-2">
            {tasks.map((t) => (
              <Link key={t.id} href={`/tasks/${t.id}`} className="flex items-center justify-between p-2 rounded hover:bg-zinc-800/50">
                <div className="flex items-center gap-2">
                  <span className="text-sm">{t.skill}</span>
                  <StatusBadge status={t.status} />
                </div>
                <span className="text-sm text-zinc-400">₹{t.price}</span>
              </Link>
            ))}
          </div>
        )}
      </Card>

      <Card>
        <h2 className="text-lg font-semibold mb-3">Ratings</h2>
        {ratings.length === 0 ? <p className="text-zinc-500 text-sm">No ratings yet</p> : (
          <div className="space-y-3">
            {ratings.map((r, i) => (
              <div key={i} className="border-b border-zinc-800 pb-3 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="text-yellow-400">{"★".repeat(r.rating)}</span>
                  <span className="text-xs text-zinc-500">{new Date(r.created_at).toLocaleDateString()}</span>
                </div>
                {r.comment && <p className="text-sm text-zinc-300 mt-1">{r.comment}</p>}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}

export default function AgentDetailPage() {
  return <ProtectedRoute><AgentDetailContent /></ProtectedRoute>;
}
