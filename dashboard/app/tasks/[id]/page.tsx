"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ProtectedRoute } from "../../lib/auth-context";
import { getTask, rateTask, getTaskChain } from "../../lib/api";
import { Navbar, timeAgo } from "../../lib/components";

interface TaskData {
  id: string; skill_requested: string; description?: string; status: string;
  quoted_price: string; actual_price?: string; currency: string;
  provider_agent_id: string; provider_agent_name?: string; provider_agent_slug?: string;
  requester_user_id: string;
  error_message?: string;
  created_at: string; completed_at?: string; escrowed_at?: string; processing_at?: string;
}

interface ChainNode {
  id: string;
  skill: string;
  agent_name?: string;
  cost?: string;
  status: string;
  duration_s?: number;
  children?: ChainNode[];
}

const STATUS_COLORS: Record<string, string> = {
  completed: "text-emerald-400", pending: "text-yellow-400", processing: "text-blue-400",
  failed: "text-red-400", timeout: "text-red-400", escrowed: "text-yellow-400",
};

const ACTIVE_STATUSES = ["pending", "escrowed", "processing", "assigned"];

function TaskDetailContent() {
  const { id } = useParams();
  const [task, setTask] = useState<TaskData | null>(null);
  const [loading, setLoading] = useState(true);
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [rated, setRated] = useState(false);
  const [rateError, setRateError] = useState("");
  const [chain, setChain] = useState<ChainNode | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set());
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchTask = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getTask(id as string);
      setTask(data);
      if (!ACTIVE_STATUSES.includes(data.status) && intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [id]);

  useEffect(() => {
    fetchTask();
    if (id) {
      getTaskChain(id as string).then(setChain).catch(() => {});
    }
    intervalRef.current = setInterval(fetchTask, 2000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [fetchTask, id]);

  const toggleNode = (nodeId: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId); else next.add(nodeId);
      return next;
    });
  };

  function calcChainTotal(node: ChainNode): number {
    const self = parseFloat(node.cost || "0");
    const childTotal = (node.children || []).reduce((sum, c) => sum + calcChainTotal(c), 0);
    return self + childTotal;
  }

  function calcChainTime(node: ChainNode): number {
    const self = node.duration_s || 0;
    const childMax = (node.children || []).reduce((m, c) => Math.max(m, calcChainTime(c)), 0);
    return self + childMax;
  }

  function renderChainNode(node: ChainNode, depth: number, isLast: boolean): React.ReactNode {
    const prefix = depth === 0 ? "" : isLast ? "└── " : "├── ";
    const statusIcon = node.status === "completed" ? "✓" : node.status === "failed" ? "✗" : "…";
    const statusColor = STATUS_COLORS[node.status] || "text-zinc-400";
    const cost = node.cost ? `${parseFloat(node.cost).toFixed(0)} credits` : "";
    const expanded = expandedNodes.has(node.id);

    return (
      <div key={node.id}>
        <button
          onClick={() => toggleNode(node.id)}
          className="flex items-center gap-2 text-sm font-mono hover:bg-[#0a1f0a]/30 px-2 py-1 rounded w-full text-left"
          style={{ paddingLeft: `${depth * 24 + 8}px` }}
        >
          <span className="text-zinc-600">{prefix}</span>
          <span className={statusColor}>●</span>
          <span className="text-white">{node.skill}</span>
          {node.agent_name && <span className="text-zinc-500">({node.agent_name})</span>}
          {cost && <><span className="text-zinc-600">───</span><span className="text-zinc-400">{cost}</span></>}
          <span className="text-zinc-600">───</span>
          <span className={statusColor}>{node.status} {statusIcon}</span>
          {node.duration_s != null && <span className="text-zinc-600 text-xs">{node.duration_s.toFixed(1)}s</span>}
        </button>
        {expanded && (
          <div className="ml-8 text-xs text-zinc-500 font-mono px-2 py-1" style={{ paddingLeft: `${depth * 24 + 32}px` }}>
            ID: {node.id}
          </div>
        )}
        {node.children?.map((child, i) => renderChainNode(child, depth + 1, i === (node.children!.length - 1)))}
      </div>
    );
  }

  const handleRate = async () => {
    if (rating === 0) { setRateError("Select a rating"); return; }
    setRateError("");
    try {
      await rateTask(id as string, rating, feedback || undefined);
      setRated(true);
    } catch (err: unknown) {
      setRateError(err instanceof Error ? err.message : "Failed to submit rating");
    }
  };

  if (loading) return <div className="max-w-3xl mx-auto px-6 pt-24 pb-16"><p className="text-zinc-500 font-mono">Loading task...</p></div>;
  if (!task) return <div className="max-w-3xl mx-auto px-6 pt-24 pb-16"><p className="text-zinc-400 font-mono">Task not found</p></div>;

  const price = parseFloat(task.quoted_price || "0");
  const durationMs = task.completed_at && task.created_at ? new Date(task.completed_at).getTime() - new Date(task.created_at).getTime() : null;
  const isActive = ACTIVE_STATUSES.includes(task.status);

  const timeline = [
    { label: "Created", time: task.created_at, done: true },
    { label: "Escrowed", time: task.escrowed_at || (["escrowed", "processing", "completed"].includes(task.status) ? task.created_at : null), done: ["escrowed", "processing", "completed", "assigned"].includes(task.status) },
    { label: "Processing", time: task.processing_at || (["processing", "completed"].includes(task.status) ? task.created_at : null), done: ["processing", "completed"].includes(task.status) },
    { label: task.status === "failed" ? "Failed" : "Completed", time: task.completed_at, done: task.status === "completed" || task.status === "failed", note: durationMs ? `${(durationMs / 1000).toFixed(1)}s` : undefined },
  ];

  return (
    <div className="max-w-3xl mx-auto px-6 pt-24 pb-16 space-y-6">
      {/* Header */}
      <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
        <div className="flex items-center gap-2 mb-2">
          <h1 className="text-lg font-bold text-white font-mono">Task</h1>
          <span className="text-xs text-zinc-500 font-mono">{task.id.slice(0, 12)}...</span>
          {isActive && <span className="ml-auto flex items-center gap-1.5 text-xs text-yellow-400"><span className="w-2 h-2 rounded-full bg-yellow-400 animate-pulse" />Live</span>}
        </div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-zinc-400">Skill:</span><span className="text-[#00ff41] font-mono">{task.skill_requested}</span>
          <span className="text-zinc-600">·</span>
          <span className="text-zinc-400">Agent:</span>
          {task.provider_agent_slug ? (
            <Link href={`/agents/${task.provider_agent_slug}`} className="text-[#00ff41] font-mono hover:underline">@{task.provider_agent_slug}</Link>
          ) : (
            <span className="text-zinc-500 font-mono text-xs">{task.provider_agent_id.slice(0, 8)}</span>
          )}
          <span className="text-zinc-600">·</span>
          <span className={`font-mono font-semibold ${STATUS_COLORS[task.status] || "text-zinc-400"}`}>● {task.status}</span>
        </div>
        <div className="text-xs text-zinc-500 mt-2">
          Posted {timeAgo(task.created_at)}
          {durationMs && <> · Completed in {(durationMs / 1000).toFixed(1)}s</>}
        </div>
      </div>

      {/* Timeline */}
      <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
        <h2 className="text-sm text-zinc-400 font-mono mb-4">// Status Timeline</h2>
        <div className="space-y-3">
          {timeline.map((step, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="flex flex-col items-center">
                <span className={`w-3 h-3 rounded-full border-2 ${step.done ? "bg-[#00ff41] border-[#00ff41]" : "bg-transparent border-zinc-600"}`} />
                {i < timeline.length - 1 && <div className={`w-0.5 h-6 ${step.done ? "bg-[#00ff41]/30" : "bg-zinc-700"}`} />}
              </div>
              <div className="flex-1 -mt-0.5">
                <div className="flex items-center gap-2">
                  <span className={`text-sm font-mono ${step.done ? "text-white" : "text-zinc-500"}`}>{step.label}</span>
                  {step.done && <span className="text-[#00ff41] text-xs">✓</span>}
                  {step.time && <span className="text-xs text-zinc-600 font-mono">{new Date(step.time).toLocaleTimeString()}</span>}
                </div>
                {step.note && step.done && <span className="text-xs text-zinc-500">({step.note})</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Task Chain */}
      {chain && chain.children && chain.children.length > 0 && (
        <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
          <h2 className="text-sm text-zinc-400 font-mono mb-4">// Task Chain</h2>
          <div className="space-y-0">
            {renderChainNode(chain, 0, true)}
          </div>
          <div className="mt-4 pt-3 border-t border-[#1a2e1a] flex items-center gap-6 text-sm font-mono">
            <span className="text-zinc-400">Total chain cost: <span className="text-[#00ff41] font-semibold">{calcChainTotal(chain).toFixed(0)} credits</span></span>
            <span className="text-zinc-400">Total chain time: <span className="text-[#00ff41] font-semibold">{calcChainTime(chain).toFixed(1)}s</span></span>
          </div>
        </div>
      )}

      {/* Error */}
      {task.error_message && (
        <div className="border border-red-500/20 bg-red-500/5 rounded-xl p-6">
          <h2 className="text-sm text-red-400 font-mono mb-2">// Error</h2>
          <p className="text-sm text-red-300 font-mono">{task.error_message}</p>
        </div>
      )}

      {/* Cost */}
      <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
        <h2 className="text-sm text-zinc-400 font-mono mb-3">// Cost</h2>
        <p className="text-sm font-mono text-white">Task cost: <span className="text-[#00ff41] font-semibold">{price.toFixed(0)} credits</span></p>
      </div>

      {/* Rating */}
      {task.status === "completed" && !rated && (
        <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6">
          <h2 className="text-sm text-zinc-400 font-mono mb-4">// Rate This Task</h2>
          {rateError && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg p-3 mb-3">{rateError}</div>}
          <div className="flex items-center gap-1 mb-4">
            {[1, 2, 3, 4, 5].map(v => (
              <button key={v} onClick={() => setRating(v)} onMouseEnter={() => setHoverRating(v)} onMouseLeave={() => setHoverRating(0)}
                className={`text-3xl transition-colors ${v <= (hoverRating || rating) ? "text-yellow-400" : "text-zinc-700"} hover:scale-110`}>★</button>
            ))}
          </div>
          <textarea value={feedback} onChange={e => setFeedback(e.target.value)} placeholder="Optional feedback..."
            rows={2} className="w-full bg-[#09090b] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 mb-3" />
          <button onClick={handleRate} className="px-5 py-2.5 bg-[#00ff41] text-black font-semibold rounded-lg text-sm hover:bg-[#00ff41]/90 transition-colors">
            Submit Rating
          </button>
        </div>
      )}
      {rated && (
        <div className="border border-[#00ff41]/20 bg-[#00ff41]/5 rounded-xl p-6 text-center">
          <p className="text-[#00ff41] font-mono">✓ Rating submitted — thank you!</p>
        </div>
      )}

      <div className="text-center">
        <Link href="/tasks" className="text-sm text-zinc-500 hover:text-[#00ff41] transition-colors">← Back to tasks</Link>
      </div>
    </div>
  );
}

export default function TaskDetailPage() {
  return (
    <div className="bg-[#09090b] min-h-screen">
      <Navbar />
      <ProtectedRoute>
        <TaskDetailContent />
      </ProtectedRoute>
    </div>
  );
}
