"use client";

import { ReactNode } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { AuthProvider, useAuth } from "./lib/auth-context";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: "◻" },
  { href: "/dashboard/agents", label: "My Agents", icon: "⬡" },
  { href: "/dashboard/external-agents", label: "External Agents", icon: "🌐", indent: true },
  { href: "/dashboard/tasks", label: "My Tasks", icon: "↗" },
  { href: "/credits", label: "Credits", icon: "◈" },
  { href: "/dashboard/webhooks", label: "Webhooks", icon: "⚡" },
];

function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="w-56 h-screen flex flex-col border-r border-[#1a2e1a] bg-[#09090b] fixed left-0 top-0">
      <div className="p-5 border-b border-[#1a2e1a]">
        <Link href="/" className="flex items-center gap-2">
          <span className="text-[#00ff41] text-xl">⬡</span>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">RentAnAgent</h1>
            <p className="text-xs text-zinc-500 font-mono mt-0.5">Agent Marketplace</p>
          </div>
        </Link>
      </div>
      <nav className="flex-1 p-3 space-y-0.5">
        {NAV.map((item) => {
          const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href) && !NAV.some(n => n.href !== item.href && n.href.startsWith(item.href) && pathname.startsWith(n.href)));
          return (
            <Link key={item.href} href={item.href}
              className={`flex items-center gap-2.5 ${item.indent ? "pl-8" : "px-3"} py-2 rounded-lg text-sm transition-colors ${active ? "bg-[#0a1f0a] text-[#00ff41] border-l-2 border-[#00ff41]" : "text-zinc-400 hover:text-[#00ff41] hover:bg-[#0a1f0a]/50"}`}>
              <span className="text-xs">{item.icon}</span>
              <span className={item.indent ? "text-xs" : ""}>{item.label}</span>
            </Link>
          );
        })}
        <div className="border-t border-[#1a2e1a] mt-3 pt-3">
          <Link href="/agents" className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-500 hover:text-[#00ff41] hover:bg-[#0a1f0a]/50 transition-colors">
            <span className="text-xs">🌐</span> Browse Marketplace
          </Link>
          <Link href="/docs" className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-zinc-500 hover:text-[#00ff41] hover:bg-[#0a1f0a]/50 transition-colors">
            <span className="text-xs">📖</span> API Docs
          </Link>
        </div>
      </nav>
      {user && (
        <div className="p-4 border-t border-[#1a2e1a]">
          <p className="text-sm text-white truncate">{user.display_name || user.email}</p>
          <p className="text-xs text-zinc-500 font-mono truncate">{user.email}</p>
          <button onClick={logout} className="text-xs text-zinc-500 hover:text-[#00ff41] mt-2 transition-colors font-mono">Sign out →</button>
        </div>
      )}
    </aside>
  );
}

function Shell({ children }: { children: ReactNode }) {
  const { token, loading } = useAuth();
  const pathname = usePathname();
  const isAuth = pathname === "/login" || pathname === "/register";
  const isPublic = pathname === "/" || pathname === "/agents" || pathname.startsWith("/agents/") && !pathname.startsWith("/agents/new")
    || pathname === "/tasks" || pathname === "/docs" || pathname === "/developers" || pathname === "/publish";
  const isDashboard = pathname.startsWith("/dashboard") || pathname === "/credits"
    || pathname === "/agents/new" || pathname === "/tasks/new" || pathname.startsWith("/tasks/");

  if (loading) return <div className="flex items-center justify-center h-screen bg-[#09090b] text-zinc-500">Loading...</div>;

  if (isAuth || isPublic) return <>{children}</>;

  if (!token && isDashboard) return <>{children}</>;

  if (token) {
    return (
      <div className="flex">
        <Sidebar />
        <main className="ml-56 flex-1 min-h-screen bg-[#09090b] p-8">{children}</main>
      </div>
    );
  }

  return <>{children}</>;
}

export function ClientLayout({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <Shell>{children}</Shell>
    </AuthProvider>
  );
}
