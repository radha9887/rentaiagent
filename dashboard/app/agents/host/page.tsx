"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { ProtectedRoute } from "../../lib/auth-context";
import { authFetch, API_URL } from "../../lib/api";
import { Button, Input, Textarea, Select, Card, StatCard } from "../../lib/ui";
import { Navbar } from "../../lib/components";

interface HostedAgent {
  id: string;
  name: string;
  slug: string;
  description: string;
  status: string;
  hosting?: {
    runtime: string;
    memory_mb: number;
    timeout_seconds: number;
    invocation_count: number;
    last_invoked: string | null;
    code_version: number;
    code_size_bytes: number;
    hosting_status: string;
  };
  skills?: { skill_tag: string; category: string }[];
  price_per_task: string;
}

interface EnvVar {
  key: string;
  value: string;
}

interface LogEntry {
  timestamp: string;
  message: string;
  level: string;
}

const STATUS_COLORS: Record<string, string> = {
  live: "bg-emerald-400",
  running: "bg-emerald-400",
  stopped: "bg-red-400",
  pending: "bg-yellow-400",
  building: "bg-yellow-400",
  failed: "bg-zinc-500",
  deploying: "bg-yellow-400",
};

const STATUS_TEXT_COLORS: Record<string, string> = {
  live: "text-emerald-400",
  running: "text-emerald-400",
  stopped: "text-red-400",
  pending: "text-yellow-400",
  building: "text-yellow-400",
  failed: "text-zinc-400",
  deploying: "text-yellow-400",
};

function StatusDot({ status }: { status: string }) {
  const s = status?.toLowerCase() || "stopped";
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`w-2 h-2 rounded-full ${STATUS_COLORS[s] || "bg-zinc-500"}`} />
      <span className={`text-xs font-mono capitalize ${STATUS_TEXT_COLORS[s] || "text-zinc-400"}`}>{s}</span>
    </span>
  );
}

/* ─── Create Form ─── */
function CreateHostedAgentForm({ onCreated }: { onCreated: (agent: HostedAgent) => void }) {
  const [form, setForm] = useState({
    name: "", description: "", price_per_task: "10",
    runtime: "python3.12", memory_mb: "256", timeout_seconds: 60,
  });
  const [skills, setSkills] = useState<{ skill_tag: string; category: string }[]>([]);
  const [skillInput, setSkillInput] = useState("");
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [step, setStep] = useState("");

  const slug = form.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }));

  const addSkill = () => {
    const tag = skillInput.trim();
    if (tag && !skills.some(s => s.skill_tag === tag)) {
      setSkills([...skills, { skill_tag: tag, category: "general" }]);
      setSkillInput("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!zipFile) {
      setError("Please select your agent source code (.zip file)");
      return;
    }
    if (skills.length === 0) {
      setError("Add at least one skill tag");
      return;
    }

    setLoading(true);
    try {
      setStep("Creating & deploying agent...");
      const token = localStorage.getItem("token") || "";

      // Single call: create + validate + deploy
      const formData = new FormData();
      const metadata = {
        name: form.name,
        slug,
        description: form.description,
        skills: skills.map(s => s.skill_tag),
        price_per_task: Number(form.price_per_task),
        runtime: form.runtime,
        memory_mb: Number(form.memory_mb),
        timeout_sec: Number(form.timeout_seconds),
      };
      formData.append("metadata", JSON.stringify(metadata));
      formData.append("file", zipFile);

      const res = await fetch(`${API_URL}/v1/agents/host/deploy`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}` },
        body: formData,
      });
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const errors = data.detail?.errors || data.detail;
        throw new Error(typeof errors === "string" ? errors : Array.isArray(errors) ? errors.join(", ") : JSON.stringify(errors) || "Failed to create agent");
      }

      // Auto-start
      setStep("Starting agent...");
      await authFetch(`/v1/agents/${data.agent_id}/start`, { method: "POST" });

      setStep("");
      onCreated({ ...data, id: data.agent_id });
      setForm({ name: "", description: "", price_per_task: "10", runtime: "python3.12", memory_mb: "256", timeout_seconds: 60 });
      setSkills([]);
      setZipFile(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create hosted agent");
      setStep("");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card>
      <h2 className="text-lg font-semibold text-white mb-4">Create New Hosted Agent</h2>
      {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg p-3 mb-4">{error}</div>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input label="Name" value={form.name} onChange={set("name")} required placeholder="My Agent" />
        <div>
          <label className="block text-sm text-zinc-400 mb-1.5">Slug</label>
          <div className="bg-zinc-900 border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-zinc-400 font-mono">{slug || "auto-generated"}</div>
        </div>
        <Textarea label="Description" value={form.description} onChange={set("description")} rows={3} placeholder="What does this agent do?" />
        <div>
          <label className="block text-sm text-zinc-400 mb-1.5">Skills</label>
          <div className="flex gap-2">
            <input value={skillInput} onChange={e => setSkillInput(e.target.value)}
              onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addSkill())}
              className="flex-1 bg-[#0a0f0a] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50"
              placeholder="e.g. summarize" />
            <Button type="button" variant="secondary" onClick={addSkill}>Add</Button>
          </div>
          {skills.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {skills.map(s => (
                <span key={s.skill_tag} className="inline-flex items-center gap-1 px-2 py-0.5 bg-[#0a1f0a] rounded text-xs text-[#00ff41] border border-[#1a2e1a] font-mono">
                  {s.skill_tag}
                  <button type="button" onClick={() => setSkills(skills.filter(x => x.skill_tag !== s.skill_tag))} className="text-zinc-500 hover:text-white ml-1">×</button>
                </span>
              ))}
            </div>
          )}
        </div>
        <Input label="Price per Task (credits)" type="number" step="0.01" value={form.price_per_task} onChange={set("price_per_task")} required />
        <div className="grid grid-cols-2 gap-4">
          <Select label="Runtime" value={form.runtime} onChange={set("runtime")}
            options={[{ value: "python3.12", label: "Python 3.12" }, { value: "python3.11", label: "Python 3.11" }]} />
          <Select label="Memory" value={form.memory_mb} onChange={set("memory_mb")}
            options={[{ value: "128", label: "128 MB — Standard" }, { value: "256", label: "256 MB — Pro" }, { value: "512", label: "512 MB — Coming Soon", disabled: true }, { value: "1024", label: "1024 MB — Coming Soon", disabled: true }]} />
        </div>
        <div>
          <label className="block text-sm text-zinc-400 mb-1.5">Timeout: {form.timeout_seconds}s</label>
          <input type="range" min={5} max={300} value={form.timeout_seconds}
            onChange={e => setForm(f => ({ ...f, timeout_seconds: parseInt(e.target.value) }))}
            className="w-full accent-[#00ff41]" />
          <div className="flex justify-between text-xs text-zinc-600 mt-1"><span>5s</span><span>300s</span></div>
        </div>
        {/* Source Code Upload */}
        <div>
          <label className="block text-sm text-zinc-400 mb-1.5">Source Code (.zip) *</label>
          <div className={`border-2 border-dashed rounded-lg p-4 text-center transition-all ${
            zipFile ? "border-[#00ff41]/40 bg-[#00ff4108]" : "border-zinc-700 hover:border-zinc-500"
          }`}>
            {zipFile ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-[#00ff41]">📦</span>
                  <span className="text-sm text-white font-mono">{zipFile.name}</span>
                  <span className="text-xs text-zinc-500">({(zipFile.size / 1024).toFixed(1)} KB)</span>
                </div>
                <button type="button" onClick={() => setZipFile(null)} className="text-zinc-500 hover:text-red-400 text-sm">✕ Remove</button>
              </div>
            ) : (
              <label className="cursor-pointer">
                <div className="text-zinc-400 text-sm mb-1">Drop your .zip here or <span className="text-[#00ff41] underline">browse</span></div>
                <div className="text-zinc-600 text-xs">Must contain handler.py + agent.json</div>
                <input type="file" accept=".zip" className="hidden" onChange={e => {
                  const f = e.target.files?.[0];
                  if (f) setZipFile(f);
                }} />
              </label>
            )}
          </div>
          <div className="mt-2 text-xs text-zinc-600 font-mono">
            Required structure: handler.py (with handle(task) function) + agent.json
          </div>
        </div>
        <div className="pt-2">
          {step && <div className="text-sm text-[#00ff41] mb-2 font-mono animate-pulse">⏳ {step}</div>}
          <Button type="submit" disabled={loading || !zipFile}>{loading ? step || "Processing..." : "Create & Deploy Agent"}</Button>
        </div>
      </form>
    </Card>
  );
}

/* ─── Upload Code ─── */
function UploadCode({ agent, onUploaded }: { agent: HostedAgent; onUploaded: () => void }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const upload = async (file: File) => {
    setError("");
    setSuccess("");
    setUploading(true);
    try {
      const token = localStorage.getItem("jwt");
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_URL}/v1/agents/${agent.id}/code`, {
        method: "PUT",
        headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: formData,
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Upload failed");
      }
      setSuccess("Code uploaded successfully! Deploying...");
      onUploaded();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-white">Upload Code (.zip)</h3>
      <div
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${dragging ? "border-[#00ff41] bg-[#00ff41]/5" : "border-[#1a2e1a] hover:border-[#00ff4155]"}`}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) upload(f); }}
        onClick={() => fileRef.current?.click()}
      >
        <input ref={fileRef} type="file" accept=".zip" className="hidden" onChange={e => { const f = e.target.files?.[0]; if (f) upload(f); }} />
        <div className="text-3xl mb-2">📦</div>
        <p className="text-sm text-zinc-400">{uploading ? "Uploading..." : "Drag & drop .zip or click to browse"}</p>
      </div>
      <div className="bg-[#0a0f0a] border border-[#1a2e1a] rounded-lg p-3 font-mono text-xs text-zinc-500">
        <p className="text-zinc-400 mb-1">Required structure:</p>
        <pre>{`my-agent/
├── handler.py         (required - handle(task) function)
├── agent.json         (required - metadata)
└── requirements.txt   (optional)`}</pre>
      </div>
      {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg p-3">{error}</div>}
      {success && <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm rounded-lg p-3">{success}</div>}
    </div>
  );
}

/* ─── Environment Variables ─── */
function EnvVarsEditor({ agent }: { agent: HostedAgent }) {
  const [vars, setVars] = useState<EnvVar[]>([{ key: "", value: "" }]);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");

  const addRow = () => setVars([...vars, { key: "", value: "" }]);
  const removeRow = (i: number) => setVars(vars.filter((_, idx) => idx !== i));
  const update = (i: number, field: "key" | "value", val: string) =>
    setVars(vars.map((v, idx) => idx === i ? { ...v, [field]: val } : v));

  const save = async () => {
    setSaving(true);
    setMsg("");
    try {
      const envObj: Record<string, string> = {};
      vars.filter(v => v.key.trim()).forEach(v => { envObj[v.key.trim()] = v.value; });
      const res = await authFetch(`/v1/agents/${agent.id}/env`, {
        method: "PUT",
        body: JSON.stringify(envObj),
      });
      if (!res.ok) throw new Error("Failed to save");
      setMsg("Environment variables saved");
    } catch {
      setMsg("Failed to save environment variables");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-white">Environment Variables</h3>
      {vars.map((v, i) => (
        <div key={i} className="flex gap-2">
          <input value={v.key} onChange={e => update(i, "key", e.target.value)} placeholder="KEY"
            className="flex-1 bg-[#0a0f0a] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50" />
          <input value={v.value} onChange={e => update(i, "value", e.target.value)} placeholder="value" type="password"
            className="flex-1 bg-[#0a0f0a] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50" />
          <button onClick={() => removeRow(i)} className="text-zinc-500 hover:text-red-400 px-2">×</button>
        </div>
      ))}
      <div className="flex gap-2">
        <Button variant="secondary" onClick={addRow}>+ Add Variable</Button>
        <Button onClick={save} disabled={saving}>{saving ? "Saving..." : "Save"}</Button>
      </div>
      {msg && <p className="text-xs text-zinc-400">{msg}</p>}
    </div>
  );
}

/* ─── Logs Viewer ─── */
function LogsViewer({ agent }: { agent: HostedAgent }) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [loading, setLoading] = useState(false);

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await authFetch(`/v1/agents/${agent.id}/logs`);
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || data.items || []);
      }
    } catch {} finally { setLoading(false); }
  }, [agent.id]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  useEffect(() => {
    if (!autoRefresh) return;
    const iv = setInterval(fetchLogs, 5000);
    return () => clearInterval(iv);
  }, [autoRefresh, fetchLogs]);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Logs</h3>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-zinc-400 cursor-pointer">
            <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)}
              className="accent-[#00ff41]" />
            Auto-refresh
          </label>
          <Button variant="ghost" onClick={fetchLogs}>{loading ? "..." : "↻"}</Button>
        </div>
      </div>
      <div className="bg-black border border-[#1a2e1a] rounded-lg p-4 font-mono text-xs max-h-80 overflow-y-auto">
        {logs.length === 0 ? (
          <p className="text-zinc-600">No logs available</p>
        ) : (
          logs.map((l, i) => (
            <div key={i} className="flex gap-2 py-0.5">
              <span className="text-zinc-600 shrink-0">{l.timestamp ? new Date(l.timestamp).toISOString().slice(11, 23) : ""}</span>
              <span className={l.level === "error" ? "text-red-400" : l.level === "warn" ? "text-yellow-400" : "text-zinc-300"}>{l.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

/* ─── Agent Detail Panel ─── */
function AgentDetailPanel({ agent, onRefresh }: { agent: HostedAgent; onRefresh: () => void }) {
  const [tab, setTab] = useState<"code" | "env" | "endpoint" | "logs">("code");
  const hosting = agent.hosting;
  const [copied, setCopied] = useState(false);

  const executeUrl = `https://host.rentaiagent.io/agents/${agent.id}`;
  const curlExample = `curl -X POST "${executeUrl}" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"skill": "your-skill", "payload": {"input": "hello"}}'`;

  const copyUrl = () => {
    navigator.clipboard.writeText(executeUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const tabs = [
    { key: "code", label: "📦 Upload Code" },
    { key: "env", label: "🔑 Env Vars" },
    { key: "endpoint", label: "🔗 Endpoint" },
    { key: "logs", label: "📋 Logs" },
  ] as const;

  return (
    <div className="space-y-4">
      {/* Stats row */}
      {hosting && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Invocations" value={hosting.invocation_count || 0} />
          <StatCard label="Code Version" value={`v${hosting.code_version || 0}`} />
          <StatCard label="Code Size" value={hosting.code_size_bytes ? `${(hosting.code_size_bytes / 1024).toFixed(1)} KB` : "—"} />
          <StatCard label="Last Invoked" value={hosting.last_invoked ? new Date(hosting.last_invoked).toLocaleDateString() : "Never"} />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[#1a2e1a] pb-px">
        {tabs.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)}
            className={`px-3 py-2 text-xs font-mono rounded-t transition-colors ${tab === t.key ? "text-[#00ff41] border-b-2 border-[#00ff41] bg-[#0a1f0a]" : "text-zinc-500 hover:text-zinc-300"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {tab === "code" && <UploadCode agent={agent} onUploaded={onRefresh} />}
      {tab === "env" && <EnvVarsEditor agent={agent} />}
      {tab === "endpoint" && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-white">Execute Endpoint</h3>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-[#0a0f0a] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono break-all">{executeUrl}</code>
            <Button variant="secondary" onClick={copyUrl}>{copied ? "Copied!" : "Copy"}</Button>
          </div>
          <div>
            <p className="text-xs text-zinc-400 mb-2">Example:</p>
            <pre className="bg-black border border-[#1a2e1a] rounded-lg p-4 font-mono text-xs text-zinc-300 overflow-x-auto">{curlExample}</pre>
          </div>
        </div>
      )}
      {tab === "logs" && <LogsViewer agent={agent} />}
    </div>
  );
}

/* ─── Hosted Agent Card ─── */
function HostedAgentCard({ agent, onRefresh, autoExpand }: { agent: HostedAgent; onRefresh: () => void; autoExpand?: boolean }) {
  const [expanded, setExpanded] = useState(autoExpand || false);
  const [actionLoading, setActionLoading] = useState("");
  const hosting = agent.hosting;
  const status = hosting?.hosting_status || "stopped";

  const action = async (act: string, method = "POST") => {
    setActionLoading(act);
    try {
      await authFetch(`/v1/agents/${agent.id}/${act}`, { method });
      onRefresh();
    } catch {} finally { setActionLoading(""); }
  };

  return (
    <Card className="!p-0 overflow-hidden">
      <div className="p-5">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[#00ff41] text-sm">⚡</span>
              <span className="text-white font-semibold">{agent.name}</span>
              <StatusDot status={status} />
            </div>
            <p className="text-xs text-zinc-500 mt-0.5 font-mono">@{agent.slug}</p>
            {agent.description && <p className="text-xs text-zinc-400 mt-2 line-clamp-2">{agent.description}</p>}
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            {status !== "running" && status !== "live" && (
              <Button variant="secondary" onClick={() => action("start")} disabled={!!actionLoading} className="!px-2 !py-1 !text-xs">
                {actionLoading === "start" ? "..." : "▶ Start"}
              </Button>
            )}
            {(status === "running" || status === "live") && (
              <Button variant="secondary" onClick={() => action("stop")} disabled={!!actionLoading} className="!px-2 !py-1 !text-xs">
                {actionLoading === "stop" ? "..." : "■ Stop"}
              </Button>
            )}
            <Button variant="ghost" onClick={() => action("hosting", "DELETE")} disabled={!!actionLoading} className="!px-2 !py-1 !text-xs text-red-400 hover:!text-red-300">
              {actionLoading === "hosting" ? "..." : "🗑"}
            </Button>
          </div>
        </div>

        {hosting && (
          <div className="flex flex-wrap gap-3 mt-3 text-xs text-zinc-500">
            <span>{hosting.runtime}</span>
            <span>·</span>
            <span>{hosting.memory_mb} MB</span>
            <span>·</span>
            <span>{hosting.invocation_count || 0} invocations</span>
            {hosting.last_invoked && <><span>·</span><span>Last: {new Date(hosting.last_invoked).toLocaleDateString()}</span></>}
          </div>
        )}

        {agent.skills && agent.skills.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-3">
            {agent.skills.map(s => (
              <span key={s.skill_tag} className="text-[10px] px-2 py-0.5 rounded bg-[#0a1f0a] text-[#00ff41] border border-[#1a2e1a] font-mono">{s.skill_tag}</span>
            ))}
          </div>
        )}

        <button onClick={() => setExpanded(!expanded)}
          className="mt-3 text-xs text-[#00ff41] hover:underline font-mono">
          {expanded ? "▲ Collapse" : "▼ Manage"}
        </button>
      </div>

      {expanded && (
        <div className="border-t border-[#1a2e1a] p-5 bg-[#060906]">
          <AgentDetailPanel agent={agent} onRefresh={onRefresh} />
        </div>
      )}
    </Card>
  );
}

/* ─── Main Page ─── */
function HostAgentContent() {
  const [agents, setAgents] = useState<HostedAgent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newAgentId, setNewAgentId] = useState<string | null>(null);

  const fetchAgents = useCallback(async () => {
    try {
      const res = await authFetch("/v1/agents/me?hosted=true");
      if (res.ok) {
        const data = await res.json();
        const agentList = data.agents || data.items || [];
        // Hosting details already included from backend
        const enriched: HostedAgent[] = agentList
          .filter((a: any) => a.hosting)
          .map((a: any) => ({
            ...a,
            hosting: {
              runtime: a.hosting.runtime,
              memory_mb: a.hosting.memory_mb,
              timeout_seconds: a.hosting.timeout_sec,
              invocation_count: a.hosting.invocation_count,
              last_invoked: a.hosting.last_invoked_at,
              code_version: a.hosting.code_version,
              code_size_bytes: a.hosting.code_size_bytes,
              hosting_status: a.hosting.deploy_status,
            },
          }));
        setAgents(enriched);
      }
    } catch {} finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchAgents(); }, [fetchAgents]);

  return (
    <div className="bg-[#09090b] min-h-screen">
      <Navbar />
      <div className="max-w-5xl mx-auto px-6 pt-24 pb-16">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white">Host an Agent</h1>
            <p className="text-zinc-400 text-sm mt-1">Upload code, we run it. Like Vercel for AI agents.</p>
          </div>
          <Button onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? "Cancel" : "+ New Hosted Agent"}
          </Button>
        </div>

        {showCreate && (
          <div className="mb-8">
            <CreateHostedAgentForm onCreated={(agent) => {
              const enriched = { ...agent, hosting: { runtime: "python3.12", memory_mb: 256, timeout_seconds: 60, invocation_count: 0, last_invoked: null, code_version: 0, code_size_bytes: 0, hosting_status: "pending" }};
              setAgents(prev => [enriched, ...prev]);
              setShowCreate(false);
              setNewAgentId(agent.id);
            }} />
          </div>
        )}

        <div className="space-y-1 mb-4">
          <h2 className="text-lg font-semibold text-white">My Hosted Agents</h2>
          <p className="text-xs text-zinc-500">{agents.length} agent{agents.length !== 1 ? "s" : ""}</p>
        </div>

        {loading ? (
          <p className="text-zinc-500 text-center py-12 font-mono">Loading...</p>
        ) : agents.length === 0 ? (
          <Card className="text-center !py-12">
            <p className="text-zinc-500 font-mono mb-4">No hosted agents yet</p>
            <Button onClick={() => setShowCreate(true)}>Create Your First Agent</Button>
          </Card>
        ) : (
          <div className="space-y-4">
            {agents.map(a => (
              <HostedAgentCard key={a.id} agent={a} onRefresh={fetchAgents} autoExpand={a.id === newAgentId} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function HostAgentPage() {
  return <ProtectedRoute><HostAgentContent /></ProtectedRoute>;
}
