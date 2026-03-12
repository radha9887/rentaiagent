"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "../../lib/auth-context";
import { registerExternalAgent, getExternalAgents, deleteExternalAgent, verifyExternalAgent, previewExternalAgent } from "../../lib/api";
import { Card, Button, Input } from "../../lib/ui";
import { StatusBadge } from "../../lib/ui";

interface AgentPreview {
  name: string;
  description: string;
  skills: string[];
  endpoint: string;
  capabilities: { streaming?: boolean; push_notifications?: boolean };
  health_ms?: number;
  healthy?: boolean;
}

interface ExternalAgent {
  id: string;
  name: string;
  description: string;
  card_url: string;
  status: string;
  skills: string[];
  endpoint: string;
  health_status: string;
  health_ms?: number;
  last_health_check?: string;
  price_per_task?: string;
  created_at: string;
}

function ExternalAgentsContent() {
  const [cardUrl, setCardUrl] = useState("");
  const [preview, setPreview] = useState<AgentPreview | null>(null);
  const [price, setPrice] = useState("");
  const [agents, setAgents] = useState<ExternalAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadAgents = async () => {
    try {
      const data = await getExternalAgents("mine=true");
      setAgents(data.items || data || []);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  };

  useEffect(() => { loadAgents(); }, []);

  const handleFetch = async () => {
    if (!cardUrl.trim()) return;
    setError("");
    setPreview(null);
    setFetching(true);
    try {
      const data = await previewExternalAgent(cardUrl);
      setPreview(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to fetch agent card");
    } finally {
      setFetching(false);
    }
  };

  const handleRegister = async () => {
    setError("");
    setSuccess("");
    setRegistering(true);
    try {
      await registerExternalAgent({ card_url: cardUrl, price_per_task: price || undefined });
      setSuccess("Agent registered successfully!");
      setPreview(null);
      setCardUrl("");
      setPrice("");
      loadAgents();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to register agent");
    } finally {
      setRegistering(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this external agent?")) return;
    try {
      await deleteExternalAgent(id);
      setAgents(prev => prev.filter(a => a.id !== id));
    } catch { /* ignore */ }
  };

  const handleVerify = async (id: string) => {
    try {
      await verifyExternalAgent(id);
      loadAgents();
    } catch { /* ignore */ }
  };

  return (
    <div>
      <div className="mb-8">
        <p className="text-[#00ff41] font-mono text-sm mb-1">{"> "}external_agents<span className="animate-pulse">_</span></p>
        <h1 className="text-2xl font-bold text-white">Register External Agent</h1>
        <p className="text-zinc-400 text-sm mt-1">Bring your own agent to the marketplace via A2A Protocol</p>
      </div>

      {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg p-3 mb-4">{error}</div>}
      {success && <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm rounded-lg p-3 mb-4">{success}</div>}

      <Card className="mb-8">
        <div className="space-y-4">
          <Input
            label="Agent Card URL"
            placeholder="https://your-server.com/.well-known/agent.json"
            value={cardUrl}
            onChange={e => setCardUrl(e.target.value)}
          />
          <Button onClick={handleFetch} disabled={fetching || !cardUrl.trim()} variant="secondary">
            {fetching ? "Fetching..." : "Fetch & Validate →"}
          </Button>

          {preview && (
            <div className="border border-[#1a2e1a] bg-[#09090b] rounded-lg p-5 space-y-3">
              <div className="text-xs text-zinc-500 font-mono uppercase tracking-wider mb-2">Preview</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                <div><span className="text-zinc-500">Name:</span> <span className="text-white">{preview.name}</span></div>
                <div><span className="text-zinc-500">Endpoint:</span> <span className="text-[#00ff41] font-mono text-xs">{preview.endpoint}</span></div>
                <div className="md:col-span-2"><span className="text-zinc-500">Description:</span> <span className="text-zinc-300">{preview.description}</span></div>
                {preview.skills?.length > 0 && (
                  <div className="md:col-span-2">
                    <span className="text-zinc-500">Skills: </span>
                    {preview.skills.map(s => (
                      <span key={s} className="inline-block text-[10px] px-2 py-0.5 rounded bg-[#0a1f0a] text-[#00ff41] border border-[#1a2e1a] font-mono mr-1 mb-1">{s}</span>
                    ))}
                  </div>
                )}
                <div>
                  <span className="text-zinc-500">Capabilities: </span>
                  <span className="text-zinc-300">
                    streaming {preview.capabilities?.streaming ? "✓" : "✗"} · push {preview.capabilities?.push_notifications ? "✓" : "✗"}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-500">Health: </span>
                  <span className={preview.healthy ? "text-emerald-400" : "text-red-400"}>
                    ● {preview.healthy ? "Healthy" : "Unreachable"}
                    {preview.health_ms != null && ` (${preview.health_ms}ms)`}
                  </span>
                </div>
              </div>
            </div>
          )}

          {preview && (
            <>
              <Input
                label="Price per task (₹)"
                placeholder="5.00"
                type="number"
                step="0.01"
                min="0"
                value={price}
                onChange={e => setPrice(e.target.value)}
              />
              <Button onClick={handleRegister} disabled={registering}>
                {registering ? "Registering..." : "Register Agent →"}
              </Button>
            </>
          )}
        </div>
      </Card>

      <div className="mb-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <span className="text-zinc-500 font-mono text-sm">//</span> Your External Agents
        </h2>
      </div>

      {loading ? (
        <p className="text-zinc-500 font-mono text-sm">Loading...</p>
      ) : agents.length === 0 ? (
        <Card>
          <p className="text-zinc-500 text-sm font-mono text-center py-4">No external agents registered yet. Add one above!</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {agents.map(agent => (
            <Card key={agent.id}>
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-white font-semibold text-sm">{agent.name || "External Agent"}</span>
                    <StatusBadge status={agent.status} />
                    <span className={`text-xs ${agent.health_status === "healthy" ? "text-emerald-400" : "text-red-400"}`}>
                      ● {agent.health_status || "unknown"}
                      {agent.health_ms != null && ` (${agent.health_ms}ms)`}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-500 font-mono">{agent.card_url}</p>
                  {agent.skills?.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {agent.skills.map(s => (
                        <span key={s} className="text-[10px] px-2 py-0.5 rounded bg-[#0a1f0a] text-[#00ff41] border border-[#1a2e1a] font-mono">{s}</span>
                      ))}
                    </div>
                  )}
                  {agent.price_per_task && <p className="text-xs text-zinc-400">₹{agent.price_per_task}/task</p>}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button variant="ghost" onClick={() => handleVerify(agent.id)}>Re-verify</Button>
                  <Button variant="ghost" onClick={() => handleDelete(agent.id)}>Delete</Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ExternalAgentsPage() {
  return <ProtectedRoute><ExternalAgentsContent /></ProtectedRoute>;
}
