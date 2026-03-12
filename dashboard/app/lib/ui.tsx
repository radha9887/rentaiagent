"use client";

import { ReactNode } from "react";

export function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    online: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    active: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    completed: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
    pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
    assigned: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    processing: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    offline: "bg-zinc-500/10 text-zinc-400 border-zinc-500/20",
    failed: "bg-red-500/10 text-red-400 border-red-500/20",
    cancelled: "bg-red-500/10 text-red-400 border-red-500/20",
  };
  const c = colors[status] || colors.offline;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${c}`}>
      {status}
    </span>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`bg-[#0a0f0a] border border-[#1a2e1a] rounded-xl p-6 hover:border-[#00ff4155] transition-colors ${className}`}>
      {children}
    </div>
  );
}

export function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Card>
      <p className="text-sm text-zinc-400 mb-1">{label}</p>
      <p className="text-2xl font-semibold text-[#00ff41] font-mono" style={{ textShadow: "0 0 6px #00ff4144" }}>{value}</p>
      {sub && <p className="text-xs text-zinc-500 mt-1">{sub}</p>}
    </Card>
  );
}

export function Button({
  children, onClick, variant = "primary", type = "button", disabled = false, className = "",
}: {
  children: ReactNode; onClick?: () => void; variant?: "primary" | "secondary" | "ghost";
  type?: "button" | "submit"; disabled?: boolean; className?: string;
}) {
  const base = "px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50";
  const variants = {
    primary: "bg-[#00ff41] text-black hover:bg-[#00ff41]/90 font-semibold",
    secondary: "border border-[#1a2e1a] text-[#00ff41] hover:bg-[#0a1f0a] hover:border-[#00ff4155]",
    ghost: "text-zinc-400 hover:text-[#00ff41] hover:bg-[#0a1f0a]",
  };
  return (
    <button type={type} onClick={onClick} disabled={disabled} className={`${base} ${variants[variant]} ${className}`}>
      {children}
    </button>
  );
}

export function Input({
  label, ...props
}: { label?: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div>
      {label && <label className="block text-sm text-zinc-400 mb-1.5">{label}</label>}
      <input
        {...props}
        className={`w-full bg-[#0a0f0a] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41] ${props.className || ""}`}
      />
    </div>
  );
}

export function Textarea({
  label, ...props
}: { label?: string } & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <div>
      {label && <label className="block text-sm text-zinc-400 mb-1.5">{label}</label>}
      <textarea
        {...props}
        className={`w-full bg-[#0a0f0a] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41] ${props.className || ""}`}
      />
    </div>
  );
}

export function Select({
  label, options, ...props
}: { label?: string; options: { value: string; label: string }[] } & React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div>
      {label && <label className="block text-sm text-zinc-400 mb-1.5">{label}</label>}
      <select
        {...props}
        className={`w-full bg-[#0a0f0a] border border-[#1a2e1a] rounded-lg px-3 py-2 text-sm text-[#00ff41] font-mono focus:outline-none focus:ring-1 focus:ring-[#00ff41]/50 focus:border-[#00ff41] ${props.className || ""}`}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  );
}
