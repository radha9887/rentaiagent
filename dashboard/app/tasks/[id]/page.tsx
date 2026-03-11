"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ProtectedRoute } from "../../lib/auth-context";
import { getTask, rateTask } from "../../lib/api";
import { Card, StatusBadge, Button } from "../../lib/ui";

interface TaskData {
  id: string; skill_requested: string; description?: string; status: string;
  quoted_price: string; actual_price?: string; platform_fee?: string; currency: string;
  provider_agent_id: string; requester_user_id: string;
  payload?: Record<string, unknown>; result?: Record<string, unknown>;
  error_message?: string;
  created_at: string; completed_at?: string;
}

function TaskDetailContent() {
  const { id } = useParams();
  const [task, setTask] = useState<TaskData | null>(null);
  const [loading, setLoading] = useState(true);
  const [rating, setRating] = useState(5);
  const [feedback, setFeedback] = useState("");
  const [rated, setRated] = useState(false);
  const [rateError, setRateError] = useState("");

  useEffect(() => {
    if (id) getTask(id as string).then(setTask).catch(() => null).finally(() => setLoading(false));
  }, [id]);

  const handleRate = async () => {
    setRateError("");
    try {
      await rateTask(id as string, rating, feedback || undefined);
      setRated(true);
    } catch (err: unknown) {
      setRateError(err instanceof Error ? err.message : "Failed to submit rating");
    }
  };

  if (loading) return <p className="text-zinc-500">Loading...</p>;
  if (!task) return <p className="text-zinc-400">Task not found</p>;

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold">{task.skill_requested || "Task"}</h1>
        <StatusBadge status={task.status} />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card>
          <p className="text-sm text-zinc-400">Task ID</p>
          <p className="text-sm font-mono text-white mt-1">{task.id}</p>
        </Card>
        <Card>
          <p className="text-sm text-zinc-400">Quoted Price</p>
          <p className="text-lg font-semibold text-white mt-1">₹{parseFloat(task.quoted_price || "0").toFixed(2)}</p>
          {task.actual_price && (
            <p className="text-xs text-zinc-500 mt-1">Actual: ₹{parseFloat(task.actual_price).toFixed(2)}</p>
          )}
        </Card>
      </div>

      <Card className="mb-6">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-zinc-400">Provider Agent:</span> <span className="text-white ml-2 font-mono text-xs">{task.provider_agent_id?.slice(0, 8) || "—"}</span></div>
          <div><span className="text-zinc-400">Currency:</span> <span className="text-white ml-2">{task.currency}</span></div>
          <div><span className="text-zinc-400">Created:</span> <span className="text-white ml-2">{new Date(task.created_at).toLocaleString()}</span></div>
          <div><span className="text-zinc-400">Completed:</span> <span className="text-white ml-2">{task.completed_at ? new Date(task.completed_at).toLocaleString() : "—"}</span></div>
          {task.platform_fee && (
            <div><span className="text-zinc-400">Platform Fee:</span> <span className="text-white ml-2">₹{parseFloat(task.platform_fee).toFixed(2)}</span></div>
          )}
        </div>
        {task.description && (
          <div className="mt-4 pt-4 border-t border-zinc-800">
            <p className="text-sm text-zinc-400 mb-1">Description</p>
            <p className="text-sm text-white">{task.description}</p>
          </div>
        )}
      </Card>

      {task.payload && Object.keys(task.payload).length > 0 && (
        <Card className="mb-6">
          <h2 className="text-sm text-zinc-400 mb-2">Payload</h2>
          <pre className="bg-black/50 rounded-lg p-4 text-xs font-mono text-zinc-300 overflow-x-auto">
            {JSON.stringify(task.payload, null, 2)}
          </pre>
        </Card>
      )}

      {task.result && Object.keys(task.result).length > 0 && (
        <Card className="mb-6">
          <h2 className="text-sm text-zinc-400 mb-2">Result</h2>
          <pre className="bg-black/50 rounded-lg p-4 text-xs font-mono text-zinc-300 overflow-x-auto">
            {JSON.stringify(task.result, null, 2)}
          </pre>
        </Card>
      )}

      {task.error_message && (
        <Card className="mb-6">
          <h2 className="text-sm text-red-400 mb-2">Error</h2>
          <p className="text-sm text-red-300">{task.error_message}</p>
        </Card>
      )}

      {task.status === "completed" && !rated && (
        <Card>
          <h2 className="text-lg font-semibold mb-3">Rate this task</h2>
          {rateError && <p className="text-red-400 text-sm mb-2">{rateError}</p>}
          <div className="flex items-center gap-2 mb-3">
            {[1, 2, 3, 4, 5].map((v) => (
              <button key={v} onClick={() => setRating(v)}
                className={`text-2xl ${v <= rating ? "text-yellow-400" : "text-zinc-600"}`}>★</button>
            ))}
          </div>
          <textarea value={feedback} onChange={(e) => setFeedback(e.target.value)} placeholder="Optional feedback..."
            className="w-full bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white mb-3" rows={2} />
          <Button onClick={handleRate}>Submit Rating</Button>
        </Card>
      )}
      {rated && <Card><p className="text-emerald-400">✓ Rating submitted!</p></Card>}
    </div>
  );
}

export default function TaskDetailPage() {
  return <ProtectedRoute><TaskDetailContent /></ProtectedRoute>;
}
