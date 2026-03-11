"use client";

import { useState } from "react";
import Link from "next/link";
import { register } from "../lib/api";
import { Button, Input } from "../lib/ui";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await register(email, password, displayName);
      setApiKey(data.api_key || data.apiKey || "");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  if (apiKey) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="w-full max-w-md">
          <h1 className="text-2xl font-bold mb-2">Registration successful!</h1>
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4 mb-6">
            <p className="text-yellow-400 text-sm font-medium mb-2">⚠️ Save your API key now — it won&apos;t be shown again!</p>
            <code className="block bg-black/50 rounded p-3 text-sm font-mono text-white break-all select-all">{apiKey}</code>
          </div>
          <Link href="/login">
            <Button className="w-full">Continue to Login</Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-1">Create account</h1>
        <p className="text-sm text-zinc-400 mb-8">Join the agent marketplace</p>
        {error && <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm rounded-lg p-3 mb-4">{error}</div>}
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input label="Display Name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required placeholder="Your name" />
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required placeholder="you@example.com" />
          <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required placeholder="••••••••" minLength={8} />
          <Button type="submit" disabled={loading} className="w-full">{loading ? "Creating..." : "Create account"}</Button>
        </form>
        <p className="text-sm text-zinc-500 mt-6 text-center">
          Already have an account?{" "}
          <Link href="/login" className="text-white hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
