"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "../lib/auth-context";
import { getBalance, getTransactions, topUp } from "../lib/api";
import { Card, StatCard, Button, Input } from "../lib/ui";

type Transaction = { id: string; type: string; amount: number; description: string; created_at: string };

function CreditsContent() {
  const [balance, setBalance] = useState(0);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [showTopUp, setShowTopUp] = useState(false);
  const [amount, setAmount] = useState("");
  const [topUpLoading, setTopUpLoading] = useState(false);

  const load = () => {
    Promise.allSettled([getBalance(), getTransactions()])
      .then(([b, t]) => {
        if (b.status === "fulfilled") setBalance(b.value.balance || 0);
        if (t.status === "fulfilled") setTransactions(Array.isArray(t.value) ? t.value : t.value.transactions || []);
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

  if (loading) return <p className="text-zinc-500">Loading...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Credits</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card className="md:col-span-2">
          <p className="text-sm text-zinc-400 mb-2">Current Balance</p>
          <p className="text-4xl font-bold text-white">₹{balance.toFixed(2)}</p>
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
        <StatCard label="Transactions" value={transactions.length} />
      </div>

      <Card className="!p-0 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-zinc-800 text-left text-xs text-zinc-500">
              <th className="px-4 py-3">Type</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Description</th>
              <th className="px-4 py-3">Date</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr><td colSpan={4} className="px-4 py-8 text-center text-zinc-500">No transactions</td></tr>
            ) : transactions.map((t) => (
              <tr key={t.id} className="border-b border-zinc-800/50">
                <td className="px-4 py-3">
                  <span className={`text-xs font-medium px-2 py-0.5 rounded ${t.type === "credit" || t.type === "topup" ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
                    {t.type}
                  </span>
                </td>
                <td className={`px-4 py-3 text-sm font-medium ${t.amount >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {t.amount >= 0 ? "+" : ""}₹{Math.abs(t.amount).toFixed(2)}
                </td>
                <td className="px-4 py-3 text-sm text-zinc-400">{t.description || "—"}</td>
                <td className="px-4 py-3 text-xs text-zinc-500">{new Date(t.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

export default function CreditsPage() {
  return <ProtectedRoute><CreditsContent /></ProtectedRoute>;
}
