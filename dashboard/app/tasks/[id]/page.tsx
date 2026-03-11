"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ProtectedRoute } from "../../lib/auth-context";
import { getTask, rateTask } from "../../lib/api";
import { Card, StatusBadge, Button } from "../../lib/ui";

function TaskDetailContent() {
  const { id } = useParams();
  const [task, setTask] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState("");
  const [rated, setRated] = useState(false);

  useEffect(() => {
    if (id) getTask(id as string).then(setTask).catch(() => null).finally(() => setLoading(false));
  }, [id]);

  const handleRate = async () => {
    try {
      await rateTask(id as string, rating, comment);
      setRated(true);
    } catch { /* ignore */ }
  };

  if (loading) return <p className="text-zinc-500">Loading...</p>;
  if (!task) return <p className="text-zinc-400">Task not found</p>;

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold">{(task.skill as string) || "Task"}</h1>
        <StatusBadge status={task.status as string} />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <Card>
          <p className="text-sm text-zinc-400">Task ID</p>
          <p className="text-sm font-mono text-white mt-1">{task.id as string}</p>
        </Card>
        <Card>
          <p className="text-sm text-zinc-400">Price</p>
          <p className="text-lg font-semibold text-white mt-1">₹{task.price as number}</p>
        </Card>
      </div>

      <Card className="mb-6">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-zinc-400">Provider:</span> <span className="text-white ml-2">{(task.provider_name as string) || "—"}</span></div>
          <div><span className="text-zinc-400">Requester:</span> <span className="text-white ml-2">{(task.requester_name as string) || "—"}</span></div>
          <div><span className="text-zinc-400">Created:</span> <span className="text-white ml-2">{new Date(task.created_at as string).toLocaleString()}</span></div>
          <div><span className="text-zinc-400">Updated:</span> <span className="text-white ml-2">{task.updated_at ? new Date(task.updated_at as string).toLocaleString() : "—"}</span></div>
        </div>
      </Card>

      {!!task.payload && (
        <Card className="mb-6">
          <h2 className="text-sm text-zinc-400 mb-2">Payload</h2>
          <pre className="bg-black/50 rounded-lg p-4 text-xs font-mono text-zinc-300 overflow-x-auto">
            {JSON.stringify(task.payload, null, 2)}
          </pre>
        </Card>
      )}

      {!!task.result && (
        <Card className="mb-6">
          <h2 className="text-sm text-zinc-400 mb-2">Result</h2>
          <pre className="bg-black/50 rounded-lg p-4 text-xs font-mono text-zinc-300 overflow-x-auto">
            {typeof task.result === "string" ? task.result : JSON.stringify(task.result, null, 2)}
          </pre>
        </Card>
      )}

      {task.status === "completed" && !task.rated && !rated && (
        <Card>
          <h2 className="text-lg font-semibold mb-3">Rate this task</h2>
          <div className="flex items-center gap-2 mb-3">
            {[1, 2, 3, 4, 5].map((v) => (
              <button key={v} onClick={() => setRating(v)}
                className={`text-2xl ${v <= rating ? "text-yellow-400" : "text-zinc-600"}`}>★</button>
            ))}
          </div>
          <textarea value={comment} onChange={(e) => setComment(e.target.value)} placeholder="Optional comment..."
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
