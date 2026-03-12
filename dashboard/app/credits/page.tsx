"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "../lib/auth-context";
import { getBalance, getTransactions, topUp } from "../lib/api";
import { Card, StatCard, Button, Input } from "../lib/ui";

type Transaction = { id: string; type: string; amount: string; description?: string; created_at: string; status: string; currency: string; };

function CreditsContent() {
  const [balance, setBalance] = useState(0);
  const [totalEarned, setTotalEarned] = useState(0);
  const [totalSpent, setTotalSpent] = useState(0);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [showTopUp, setShowTopUp] = useState(false);
  const [amount, setAmount] = useState("");
  const [topUpLoading, setTopUpLoading] = useState(false);

  const load = () => {
    Promise.allSettled([getBalance(), getTransactions()])
      .then(([b, t]) => {
        if (b.status === "fulfilled") {
          setBalance(parseFloat(b.value.balance) || 0);
          setTotalEarned(parseFloat(b.value.total_earned) || 0);
          setTotalSpent(parseFloat(b.value.total_spent) || 0);
        }
        if (t.status === "fulfilled") {
          const data = t.value;
          setTransactions(data.items || (Array.isArray(data) ? data : []));
        }
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleTopUp = async () => {
    setTopUpLoading(true);
    try {
      await topUp(parseFloat(amount));
      setShowTopUp(false);
      setAmount("");
      load();
    } catch { /* ignore */ }
    setTopUpLoading(false);
  };

  if (loading) return <p className="text-zinc-500 font-mono">Loading...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-white">Credits</h1>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="md:col-span-2">
          <p className="text-sm text-zinc-400 mb-2">Current Balance</p>
          <p className="text-4xl font-bold text-[#00ff41] font-mono" style={{ textShadow: "0 0 10px #00ff4133" }}>₹{balance.toFixed(2)}</p>
          <div className="mt-4">
            {!showTopUp ? (
              <Button onClick={() => setShowTopUp(true)}>Top Up</Button>
            ) : (
              <div className="flex items-end gap-3">
                <Input label="Amount (₹)" type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="100" />
                <Button onClick={handleTopUp} disabled={topUpLoading || !amount}>{topUpLoading ? "..." : "Add"}</Button>
                <Button variant="ghost" onClick={() => setShowTopUp(false)}>Cancel</Button>
              </div>
            )}
          </div>
        </Card>
        <StatCard label="Total Earned" value={`₹${totalEarned.toFixed(2)}`} />
        <StatCard label="Total Spent" value={`₹${totalSpent.toFixed(2)}`} />
      </div>

      <div className="border border-[#1a2e1a] rounded-xl overflow-hidden bg-[#0a0f0a]">
        <div className="grid grid-cols-12 gap-2 px-5 py-3 border-b border-[#1a2e1a] text-[10px] font-mono text-zinc-500 uppercase tracking-wider">
          <div className="col-span-2">Type</div>
          <div className="col-span-2">Amount</div>
          <div className="col-span-2">Status</div>
          <div className="col-span-3">Description</div>
          <div className="col-span-3 text-right">Date</div>
        </div>
        {transactions.length === 0 ? (
          <div className="px-5 py-12 text-center text-zinc-500 font-mono text-sm">No transactions yet</div>
        ) : transactions.map((t, i) => {
          const amt = parseFloat(t.amount) || 0;
          const isCredit = t.type === "topup" || t.type === "credit" || t.type === "earning";
          return (
            <div key={t.id} className={`grid grid-cols-12 gap-2 px-5 py-3 items-center ${i < transactions.length - 1 ? "border-b border-[#1a2e1a]/50" : ""} hover:bg-[#0a1f0a]/30 transition-colors`}>
              <div className="col-span-2">
                <span className={`text-xs font-mono font-medium px-2 py-0.5 rounded ${isCredit ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-red-500/10 text-red-400 border border-red-500/20"}`}>
                  {t.type}
                </span>
              </div>
              <div className={`col-span-2 text-sm font-mono font-medium ${isCredit ? "text-emerald-400" : "text-red-400"}`}>
                {isCredit ? "+" : "-"}₹{Math.abs(amt).toFixed(2)}
              </div>
              <div className="col-span-2 text-xs text-zinc-500 font-mono">{t.status}</div>
              <div className="col-span-3 text-sm text-zinc-400">{t.description || "—"}</div>
              <div className="col-span-3 text-right text-xs text-zinc-500 font-mono">{new Date(t.created_at).toLocaleString()}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function CreditsPage() {
  return <ProtectedRoute><CreditsContent /></ProtectedRoute>;
}
