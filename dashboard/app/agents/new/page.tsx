"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ProtectedRoute } from "../../lib/auth-context";
import { createAgent } from "../../lib/api";
import { Button, Input, Textarea, Select, Card } from "../../lib/ui";

function RegisterAgentContent() {
  const router = useRouter();
  const [form, setForm] = useState({
    name: "", description: "", endpoint_url: "", pricing_model: "per_task",
    price: "", framework: "custom", protocols: "a2a",
  });
  const [skills, setSkills] = useState<string[]>([]);
  const [skillInput, setSkillInput] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const slug = form.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const addSkill = () => {
    if (skillInput.trim() && !skills.includes(skillInput.trim())) {
      setSkills([...skills, skillInput.trim()]);
      setSkillInput("");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await createAgent({
        ...form,
        slug,
        price: parseFloat(form.price),
        skills,
        protocols: [form.protocols],
      });
      router.push("/agents");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create agent");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">Register New Agent</h1>
      {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg p-3 mb-4">{error}</div>}
      <Card>
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Name" value={form.name} onChange={set("name")} required placeholder="My Agent" />
          <div>
            <label className="block text-sm text-zinc-400 mb-1.5">Slug</label>
            <div className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-400 font-mono">{slug || "auto-generated"}</div>
          </div>
          <Textarea label="Description" value={form.description} onChange={set("description")} rows={3} placeholder="What does this agent do?" />
          <Input label="Endpoint URL" value={form.endpoint_url} onChange={set("endpoint_url")} required placeholder="https://your-agent.com/a2a" />
          <div className="grid grid-cols-2 gap-4">
            <Select label="Pricing Model" value={form.pricing_model} onChange={set("pricing_model")}
              options={[{ value: "per_task", label: "Per Task" }, { value: "per_minute", label: "Per Minute" }, { value: "per_token", label: "Per Token" }]} />
            <Input label="Price (₹)" type="number" step="0.01" value={form.price} onChange={set("price")} required placeholder="10.00" />
          </div>
          <div>
            <label className="block text-sm text-zinc-400 mb-1.5">Skills</label>
            <div className="flex gap-2">
              <input
                value={skillInput} onChange={(e) => setSkillInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), addSkill())}
                className="flex-1 bg-zinc-900 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-zinc-500"
                placeholder="Add a skill..."
              />
              <Button type="button" variant="secondary" onClick={addSkill}>Add</Button>
            </div>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {skills.map((s) => (
                <span key={s} className="inline-flex items-center gap-1 px-2 py-0.5 bg-zinc-800 rounded text-xs text-zinc-300">
                  {s}
                  <button type="button" onClick={() => setSkills(skills.filter((x) => x !== s))} className="text-zinc-500 hover:text-white">×</button>
                </span>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <Select label="Framework" value={form.framework} onChange={set("framework")}
              options={[{ value: "custom", label: "Custom" }, { value: "langchain", label: "LangChain" }, { value: "crewai", label: "CrewAI" }, { value: "autogen", label: "AutoGen" }]} />
            <Select label="Protocol" value={form.protocols} onChange={set("protocols")}
              options={[{ value: "a2a", label: "A2A" }, { value: "mcp", label: "MCP" }]} />
          </div>
          <div className="flex gap-3 pt-2">
            <Button type="submit" disabled={loading}>{loading ? "Creating..." : "Register Agent"}</Button>
            <Button type="button" variant="ghost" onClick={() => router.back()}>Cancel</Button>
          </div>
        </form>
      </Card>
    </div>
  );
}

export default function NewAgentPage() {
  return <ProtectedRoute><RegisterAgentContent /></ProtectedRoute>;
}
