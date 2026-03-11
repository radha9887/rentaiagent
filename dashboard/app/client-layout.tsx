"use client";

import { ReactNode } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { AuthProvider, useAuth } from "./lib/auth-context";

const NAV = [
  { href: "/", label: "Dashboard", icon: "◻" },
  { href: "/agents", label: "Agents", icon: "⬡" },
  { href: "/tasks", label: "Tasks", icon: "↗" },
  { href: "/credits", label: "Credits", icon: "◈" },
];

function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <aside className="w-56 h-screen flex flex-col border-r border-zinc-800 bg-[#0a0a0b] fixed left-0 top-0">
      <div className="p-5 border-b border-zinc-800">
        <h1 className="text-lg font-bold tracking-tight">RentAnAgent</h1>
        <p className="text-xs text-zinc-500 mt-0.5">Agent Marketplace</p>
      </div>
      <nav className="flex-1 p-3 space-y-0.5">
        {NAV.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                active ? "bg-zinc-800 text-white" : "text-zinc-400 hover:text-white hover:bg-zinc-800/50"
              }`}
            >
              <span className="text-xs">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>
      {user && (
        <div className="p-4 border-t border-zinc-800">
          <p className="text-sm text-white truncate">{user.display_name || user.email}</p>
          <p className="text-xs text-zinc-500 truncate">{user.email}</p>
          <button onClick={logout} className="text-xs text-zinc-500 hover:text-white mt-2 transition-colors">
            Sign out
          </button>
        </div>
      )}
    </aside>
  );
}

function Shell({ children }: { children: ReactNode }) {
  const { token, loading } = useAuth();
  const pathname = usePathname();
  const isAuth = pathname === "/login" || pathname === "/register";

  if (loading) return <div className="flex items-center justify-center h-screen text-zinc-500">Loading...</div>;
  if (!token && !isAuth) return <>{children}</>;
  if (isAuth) return <>{children}</>;

  return (
    <div className="flex">
      <Sidebar />
      <main className="ml-56 flex-1 min-h-screen p-8">{children}</main>
    </div>
  );
}

export function ClientLayout({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <Shell>{children}</Shell>
    </AuthProvider>
  );
}
