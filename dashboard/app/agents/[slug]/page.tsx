"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ProtectedRoute } from "../../lib/auth-context";
import { getAgent, getAgentRatings } from "../../lib/api";
import { Card, StatCard, StatusBadge } from "../../lib/ui";

interface Skill { id: string; skill_tag: string; category?: string; proficiency: number; task_count: number; success_rate: number; }
interface Stats { total_tasks: number; completed_tasks: number; failed_tasks: number; avg_rating: number; avg_response_ms: number; acceptance_rate: number; total_earned: string; rating_count: number; }
interface Rating { id: string; overall_score: number; feedback?: string; created_at: string; }
interface AgentData {
  id: string; name: string; slug: string; description?: string; status: string;
  endpoint_type: string; pricing_model: string; price_per_task: string; currency: string;
  protocols: string[]; framework?: string; skills: Skill[]; stats?: Stats;
}

function AgentDetailContent() {
  const { slug } = useParams();
  const [agent, setAgent] = useState<AgentData | null>(null);
  const [ratings, setRatings] = useState<Rating[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!slug) return;
    Promise.allSettled([
      getAgent(slug as string),
      getAgentRatings(slug as string),
    ]).then(([a, r]) => {
      if (a.status === "fulfilled") setAgent(a.value);
      if (r.status === "fulfilled") {
        const rData = r.value;
        setRatings(rData.items || (Array.isArray(rData) ? rData : []));
      }
    }).finally(() => setLoading(false));
  }, [slug]);

  if (loading) return <p className="text-zinc-500">Loading...</p>;
  if (!agent) return <p className="text-zinc-400">Agent not found</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{agent.name}</h1>
            <StatusBadge status={agent.status} />
          </div>
          <p className="text-sm text-zinc-500 font-mono mt-1">{agent.slug}</p>
        </div>
        <Link href={`/tasks/new?agent=${agent.id}&name=${encodeURIComponent(agent.name)}`}
          className="px-4 py-2 bg-white text-black rounded-lg text-sm font-medium hover:bg-zinc-200 transition-colors">
          Post Task
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Tasks" value={agent.stats?.total_tasks || 0} />
        <StatCard label="Rating" value={agent.stats?.avg_rating ? `★ ${agent.stats.avg_rating.toFixed(1)}` : "★ —"} sub={agent.stats?.rating_count ? `${agent.stats.rating_count} ratings` : undefined} />
        <StatCard label="Price" value={`₹${parseFloat(agent.price_per_task || "0").toFixed(2)}`} sub={agent.pricing_model} />
        <StatCard label="Protocol" value={agent.protocols?.[0] || "a2a"} />
      </div>

      <Card className="mb-6">
        <h2 className="text-sm text-zinc-400 mb-2">Description</h2>
        <p className="text-white">{agent.description || "No description"}</p>
        <h2 className="text-sm text-zinc-400 mt-4 mb-2">Skills</h2>
        <div className="flex flex-wrap gap-1.5">
          {(agent.skills || []).length === 0 ? (
            <span className="text-zinc-500 text-sm">No skills defined</span>
          ) : agent.skills.map((s) => (
            <span key={s.id} className="px-2 py-1 bg-zinc-800 rounded text-xs text-zinc-300">
              {s.skill_tag}
              {s.category && <span className="text-zinc-500 ml-1">({s.category})</span>}
            </span>
          ))}
        </div>
        {agent.framework && (
          <>
            <h2 className="text-sm text-zinc-400 mt-4 mb-2">Framework</h2>
            <p className="text-white text-sm">{agent.framework}</p>
          </>
        )}
      </Card>

      {agent.stats && (
        <Card className="mb-6">
          <h2 className="text-lg font-semibold mb-3">Stats</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><span className="text-zinc-400">Completed:</span> <span className="text-white ml-1">{agent.stats.completed_tasks}</span></div>
            <div><span className="text-zinc-400">Failed:</span> <span className="text-white ml-1">{agent.stats.failed_tasks}</span></div>
            <div><span className="text-zinc-400">Acceptance:</span> <span className="text-white ml-1">{(agent.stats.acceptance_rate * 100).toFixed(0)}%</span></div>
            <div><span className="text-zinc-400">Avg Response:</span> <span className="text-white ml-1">{agent.stats.avg_response_ms.toFixed(0)}ms</span></div>
            <div><span className="text-zinc-400">Total Earned:</span> <span className="text-white ml-1">₹{parseFloat(agent.stats.total_earned || "0").toFixed(2)}</span></div>
          </div>
        </Card>
      )}

      <Card>
        <h2 className="text-lg font-semibold mb-3">Ratings</h2>
        {ratings.length === 0 ? <p className="text-zinc-500 text-sm">No ratings yet</p> : (
          <div className="space-y-3">
            {ratings.map((r) => (
              <div key={r.id} className="border-b border-zinc-800 pb-3 last:border-0">
                <div className="flex items-center gap-2">
                  <span className="text-yellow-400">{"★".repeat(Math.round(r.overall_score))}</span>
                  <span className="text-sm text-zinc-400">{r.overall_score.toFixed(1)}</span>
                  <span className="text-xs text-zinc-500">{new Date(r.created_at).toLocaleDateString()}</span>
                </div>
                {r.feedback && <p className="text-sm text-zinc-300 mt-1">{r.feedback}</p>}
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
