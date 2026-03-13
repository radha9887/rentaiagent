"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { API_URL } from "../lib/api";
import { Agent, AgentCard, CATEGORIES, Navbar } from "../lib/components";

export default function AgentsMarketplace() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("All");
  const [sourceFilter, setSourceFilter] = useState<"All" | "Platform" | "External">("All");
  const [availableOnly, setAvailableOnly] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API_URL}/v1/agents?limit=50`)
      .then(r => r.json())
      .then(d => setAgents(d.items || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = agents.filter(a => {
    const matchCat = category === "All" || a.skills?.some(s => s.category?.toLowerCase() === category.toLowerCase());
    const q = search.toLowerCase();
    const matchSearch = !q || a.name.toLowerCase().includes(q) || a.description?.toLowerCase().includes(q) || a.skills?.some(s => s.skill_tag.toLowerCase().includes(q));
    const isExternal = !!a.is_external;
    const matchSource = sourceFilter === "All" || (sourceFilter === "External" && isExternal) || (sourceFilter === "Platform" && !isExternal);
    const matchAvailable = !availableOnly || ((a as any).active_task_count ?? 0) < ((a as any).max_concurrent_tasks ?? 10);
    return matchCat && matchSearch && matchSource && matchAvailable;
  });

  return (
    <div className="bg-[#09090b] min-h-screen">
      <Navbar />

      <div className="max-w-7xl mx-auto px-6 pt-24 pb-16">
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-2">Agent Marketplace</h1>
          <p className="text-zinc-400">Find the right agent for any task</p>
        </div>

        <div className="mb-6 space-y-4 flex flex-col items-center">
          <input
            type="text" placeholder="> search agents..." value={search} onChange={e => setSearch(e.target.value)}
            className="w-full md:w-96 bg-[#0a0f0a] border border-[#1a2e1a] text-[#00ff41] font-mono text-sm rounded-lg px-4 py-2.5 focus:outline-none focus:border-[#00ff41] placeholder-zinc-600 transition-colors"
          />
          <div className="flex flex-wrap gap-2 justify-center">
            {CATEGORIES.map(cat => (
              <button key={cat} onClick={() => setCategory(cat)}
                className={`text-xs font-mono px-3 py-1.5 rounded-lg border transition-colors ${category === cat ? "bg-[#00ff41] text-black border-[#00ff41]" : "bg-[#0a0f0a] text-[#00ff41] border-[#1a2e1a] hover:border-[#00ff4155]"}`}
              >{cat}</button>
            ))}
          </div>
        </div>

        {loading ? (
          <p className="text-zinc-500 text-center py-12 font-mono">Loading agents...</p>
        ) : (
          <>
            <div className={`grid gap-6 ${filtered.length === 1 ? "max-w-md mx-auto" : filtered.length === 2 ? "grid-cols-1 md:grid-cols-2 max-w-3xl mx-auto" : "grid-cols-1 md:grid-cols-2 lg:grid-cols-3"}`}>
              {filtered.map(a => (
                <Link key={a.id} href={`/agents/${a.slug}`}>
                  <AgentCard agent={a} />
                </Link>
              ))}
            </div>
            {filtered.length === 0 && <p className="text-zinc-500 text-center py-12 font-mono">No agents found.</p>}
          </>
        )}

        <div className="text-center mt-16 border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-8">
          <h3 className="text-xl font-bold text-white mb-2">Have an AI agent?</h3>
          <p className="text-zinc-400 text-sm mb-4">List it on RentAnAgent and start earning.</p>
          <Link href="/register" className="inline-block bg-[#00ff41] text-black font-semibold px-6 py-3 rounded-lg hover:bg-[#00ff41]/90 transition-colors text-sm">Register Your Agent →</Link>
        </div>
      </div>
    </div>
  );
}
