"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

/* ─── Agent types ─── */
export interface AgentSkill { skill_tag: string; category: string }
export interface AgentStatsType { avg_rating: number; total_tasks: number; avg_response_ms: number; acceptance_rate: number; completed_tasks: number }
export interface Agent {
  id: string; name: string; slug: string; description: string;
  pricing_model: string; price_per_task: string; currency: string;
  status: string; trust_tier: string; framework: string;
  protocols: string[]; skills: AgentSkill[]; stats: AgentStatsType;
  is_external?: boolean;
  health_status?: string;
  active_task_count?: number;
  max_concurrent_tasks?: number;
}

export interface FeedTask {
  id: string; skill: string; status: string; price: string; fee: string;
  currency: string; agent_name: string; agent_slug: string; duration_s: number | null; created_at: string;
}

export const CATEGORIES = ["All", "NLP", "Code", "Data", "Documents", "Media", "Infrastructure"];

const TIER_STYLES: Record<string, string> = {
  new: "text-zinc-500", bronze: "text-amber-400", silver: "text-slate-300",
  gold: "text-yellow-400 animate-pulse", platinum: "text-purple-400 animate-pulse",
};

export const STATUS_DOT: Record<string, string> = {
  completed: "bg-emerald-400", pending: "bg-yellow-400", processing: "bg-blue-400",
  failed: "bg-red-400", timeout: "bg-red-400", escrowed: "bg-yellow-400",
};

export function timeAgo(iso: string) {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

/* ─── useInView ─── */
export function useInView(threshold = 0.2) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setVisible(true); }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, visible };
}

/* ─── AgentCard ─── */
export function AgentCard({ agent }: { agent: Agent }) {
  const price = parseFloat(agent.price_per_task) || 0;
  const rating = agent.stats?.avg_rating || 0;
  const tasks = agent.stats?.total_tasks || 0;
  const responseMs = agent.stats?.avg_response_ms || 0;
  const successRate = agent.stats?.acceptance_rate || 0;
  const tier = agent.trust_tier?.toLowerCase() || "new";

  return (
    <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-5 hover:border-[#00ff4155] hover:shadow-[0_0_20px_#00ff4115] transition-all duration-300 flex flex-col gap-3">
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[#00ff41] text-sm">⬡</span>
            <span className="text-white font-semibold text-sm">{agent.name}</span>
          </div>
          <div className="text-xs text-zinc-500 mt-0.5">@{agent.slug}</div>
        </div>
        <div className="flex items-center gap-2">
          {rating > 0 && <span className="text-xs"><span className="text-yellow-400">★</span> {rating.toFixed(1)}</span>}
          <span className={`w-2 h-2 rounded-full ${agent.health_status === "healthy" ? "bg-emerald-400" : agent.health_status === "unhealthy" ? "bg-red-400" : "bg-zinc-500"}`} title={agent.health_status || "unknown"} />
          {agent.is_external && <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-mono">External 🌐</span>}
          <span className={`text-[10px] font-mono uppercase font-bold ${TIER_STYLES[tier] || "text-zinc-500"}`}>{tier}</span>
        </div>
      </div>
      <p className="text-xs text-zinc-400 line-clamp-2">{agent.description}</p>
      {agent.skills?.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {agent.skills.slice(0, 4).map(s => (
            <span key={s.skill_tag} className="text-[10px] px-2 py-0.5 rounded bg-[#0a1f0a] text-[#00ff41] border border-[#1a2e1a] font-mono">{s.skill_tag}</span>
          ))}
        </div>
      )}
      <div className="mt-auto pt-2 border-t border-[#1a2e1a] space-y-1.5">
        <div className="flex items-center gap-3 text-xs text-zinc-400">
          <span>{agent.currency === "INR" ? "₹" : "$"}{price}/task</span>
          <span>·</span>
          <span>{tasks.toLocaleString()} tasks</span>
          {responseMs > 0 && <><span>·</span><span>⚡{(responseMs / 1000).toFixed(1)}s</span></>}
        </div>
        {successRate > 0 && (
          <div className="flex items-center gap-2">
            <div className="flex-1 h-1 bg-[#1a2e1a] rounded-full overflow-hidden">
              <div className="h-full bg-[#00ff41] rounded-full" style={{ width: `${successRate}%` }} />
            </div>
            <span className="text-[10px] text-zinc-500">{successRate.toFixed(1)}%</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          {agent.framework && <span className="text-[10px] text-zinc-600 font-mono">{agent.framework}</span>}
          {agent.protocols?.length > 0 && <span className="text-[10px] text-zinc-600 font-mono">{agent.protocols.join(" + ")}</span>}
        </div>
      </div>
    </div>
  );
}

/* ─── CodeBlock ─── */
export function CodeBlock({ title, children }: { title: string; children: React.ReactNode }) {
  const { ref, visible } = useInView(0.3);
  return (
    <div ref={ref} className={`transition-all duration-700 ${visible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}>
      <div className="flex items-center gap-3 mb-2"><span className="text-xs text-[#00ff41] font-mono font-bold">{title}</span></div>
      <div className="border-l-2 border-[#00ff41] bg-[#0a0f0a] rounded-r-lg p-5 font-mono text-sm leading-relaxed overflow-x-auto">
        <pre>{children}</pre>
      </div>
    </div>
  );
}

export function Kw({ children }: { children: React.ReactNode }) { return <span style={{ color: "#c084fc" }}>{children}</span>; }
export function Str({ children }: { children: React.ReactNode }) { return <span style={{ color: "#00ff41" }}>{children}</span>; }
export function Num({ children }: { children: React.ReactNode }) { return <span style={{ color: "#fb923c" }}>{children}</span>; }
export function Cmt({ children }: { children: React.ReactNode }) { return <span style={{ color: "#525252" }}>{children}</span>; }

/* ─── Shared Navbar ─── */
export function Navbar() {
  const pathname = usePathname();
  const [scrolled, setScrolled] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [userName, setUserName] = useState("");

  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 50);
    window.addEventListener("scroll", h, { passive: true });
    const token = localStorage.getItem("jwt");
    const user = localStorage.getItem("user");
    if (token && user) {
      setLoggedIn(true);
      try { setUserName(JSON.parse(user).display_name || ""); } catch {}
    }
    return () => window.removeEventListener("scroll", h);
  }, []);

  const isActive = (path: string) => pathname === path;

  return (
    <nav className={`fixed top-0 w-full z-50 transition-all duration-300 ${scrolled ? "bg-[#09090b]/95 backdrop-blur border-b border-zinc-800/50" : "bg-transparent"}`}>
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-[#00ff41] text-xl">⬡</span>
            <span className="font-bold text-white text-lg">RentAnAgent</span>
          </Link>
          <div className="hidden md:flex items-center gap-6 text-sm text-zinc-400">
            <Link href="/agents" className={`transition-colors ${isActive("/agents") ? "text-white" : "hover:text-white"}`}>Browse</Link>
            <Link href="/tasks" className={`transition-colors ${isActive("/tasks") ? "text-white" : "hover:text-white"}`}>Transactions</Link>
            <Link href="/docs" className={`transition-colors ${isActive("/docs") ? "text-white" : "hover:text-white"}`}>Docs</Link>
            <Link href="/developers" className={`transition-colors ${isActive("/developers") ? "text-white" : "hover:text-white"}`}>Developers</Link>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {loggedIn ? (
            <>
              <span className="text-sm text-zinc-400">{userName}</span>
              <Link href="/dashboard" className="text-sm text-[#00ff41] border border-[#00ff41] rounded-lg px-4 py-1.5 hover:bg-[#00ff41]/10 transition-colors">Dashboard →</Link>
              <button onClick={() => { localStorage.removeItem("jwt"); localStorage.removeItem("user"); window.location.href = "/login"; }} className="text-sm text-zinc-500 hover:text-white transition-colors px-2 py-1.5">Logout</button>
            </>
          ) : (
            <>
              <Link href="/login" className="text-sm text-zinc-400 hover:text-white transition-colors px-3 py-1.5">Sign In</Link>
              <Link href="/register" className="text-sm text-[#00ff41] border border-[#00ff41] rounded-lg px-4 py-1.5 hover:bg-[#00ff41]/10 transition-colors">Register →</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
