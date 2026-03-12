"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "../../lib/auth-context";
import { createWebhook, getWebhooks, deleteWebhook, testWebhook } from "../../lib/api";
import { Card, Button, Input } from "../../lib/ui";
import { timeAgo } from "../../lib/components";

interface Webhook {
  id: string;
  callback_url: string;
  events: string[];
  status: string;
  failure_count: number;
  last_triggered_at?: string;
  created_at: string;
}

const EVENT_OPTIONS = [
  { value: "task.completed", label: "task.completed" },
  { value: "task.failed", label: "task.failed" },
  { value: "task.progress", label: "task.progress" },
  { value: "task.created", label: "task.created" },
];

function WebhooksContent() {
  const [webhooks, setWebhooks] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(true);
  const [callbackUrl, setCallbackUrl] = useState("");
  const [selectedEvents, setSelectedEvents] = useState<string[]>(["task.completed", "task.failed"]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadWebhooks = async () => {
    try {
      const data = await getWebhooks();
      setWebhooks(data.items || data || []);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { loadWebhooks(); }, []);

  const toggleEvent = (event: string) => {
    setSelectedEvents(prev =>
      prev.includes(event) ? prev.filter(e => e !== event) : [...prev, event]
    );
  };

  const handleCreate = async () => {
    if (!callbackUrl.trim() || selectedEvents.length === 0) return;
    setError("");
    setSuccess("");
    setCreating(true);
    try {
      await createWebhook({ callback_url: callbackUrl, events: selectedEvents });
      setSuccess("Webhook created!");
      setCallbackUrl("");
      loadWebhooks();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create webhook");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this webhook?")) return;
    try {
      await deleteWebhook(id);
      setWebhooks(prev => prev.filter(w => w.id !== id));
    } catch { /* ignore */ }
  };

  const handleTest = async (id: string) => {
    try {
      await testWebhook(id);
      setSuccess("Test webhook sent!");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to test webhook");
    }
  };

  return (
    <div>
      <div className="mb-8">
        <p className="text-[#00ff41] font-mono text-sm mb-1">{"> "}webhooks<span className="animate-pulse">_</span></p>
        <h1 className="text-2xl font-bold text-white">Webhooks</h1>
        <p className="text-zinc-400 text-sm mt-1">Get notified when tasks complete, fail, or update.</p>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg p-3 mb-4">{error}</div>}
      {success && <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm rounded-lg p-3 mb-4">{success}</div>}

      <Card className="mb-8">
        <div className="space-y-4">
          <Input
            label="Callback URL"
            placeholder="https://your-server.com/webhook"
            value={callbackUrl}
            onChange={e => setCallbackUrl(e.target.value)}
          />
          <div>
            <label className="block text-sm text-zinc-400 mb-2">Events</label>
            <div className="flex flex-wrap gap-2">
              {EVENT_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => toggleEvent(opt.value)}
                  className={`text-xs font-mono px-3 py-1.5 rounded-lg border transition-colors ${
                    selectedEvents.includes(opt.value)
                      ? "bg-[#00ff41]/10 text-[#00ff41] border-[#00ff41]/30"
                      : "text-zinc-500 border-[#1a2e1a] hover:border-[#00ff4155]"
                  }`}
                >
                  {selectedEvents.includes(opt.value) ? "✓ " : ""}{opt.label}
                </button>
              ))}
            </div>
          </div>
          <Button onClick={handleCreate} disabled={creating || !callbackUrl.trim() || selectedEvents.length === 0}>
            {creating ? "Creating..." : "Create Webhook →"}
          </Button>
        </div>
      </Card>

      <div className="mb-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <span className="text-zinc-500 font-mono text-sm">//</span> Active Webhooks
        </h2>
      </div>

      {loading ? (
        <p className="text-zinc-500 font-mono text-sm">Loading...</p>
      ) : webhooks.length === 0 ? (
        <Card>
          <p className="text-zinc-500 text-sm font-mono text-center py-4">No webhooks configured yet. Create one above!</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {webhooks.map(wh => (
            <Card key={wh.id}>
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div className="space-y-1">
                  <p className="text-sm text-[#00ff41] font-mono break-all">{wh.callback_url}</p>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-400">
                    <span>Events: {wh.events?.join(", ") || "—"}</span>
                    <span className="text-zinc-600">·</span>
                    {wh.last_triggered_at && <span>Last triggered: {timeAgo(wh.last_triggered_at)}</span>}
                    {!wh.last_triggered_at && <span>Never triggered</span>}
                    <span className="text-zinc-600">·</span>
                    <span>Failures: {wh.failure_count || 0}</span>
                    <span className="text-zinc-600">·</span>
                    <span className={wh.status === "active" ? "text-emerald-400" : "text-red-400"}>
                      ● {wh.status || "active"}
                    </span>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button variant="ghost" onClick={() => handleTest(wh.id)}>Test</Button>
                  <Button variant="ghost" onClick={() => handleDelete(wh.id)}>Delete</Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default function WebhooksPage() {
  return <ProtectedRoute><WebhooksContent /></ProtectedRoute>;
}
