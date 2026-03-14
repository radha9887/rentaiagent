"use client";

import { Navbar } from "../lib/components";

export default function WhyPage() {
  return (
    <div className="min-h-screen bg-[#09090b] text-white">
      <Navbar />

      {/* ─── Hero ─── */}
      <section className="max-w-3xl mx-auto px-6 pt-28 pb-20 text-center">
        <h1 className="text-3xl md:text-5xl font-bold mb-4">
          Every AI tool needs a separate subscription.
          <br /><span className="text-[#00ff41]">Not anymore.</span>
        </h1>
        <p className="text-zinc-400 text-base mt-4">
          RentAiAgent is a marketplace where you use any AI agent — and only pay when you actually use it.
        </p>
      </section>

      {/* ─── The Problem (visual) ─── */}
      <section className="max-w-4xl mx-auto px-6 pb-20">
        <div className="grid md:grid-cols-2 gap-6">

          {/* Without */}
          <div className="border border-red-400/20 bg-red-400/5 rounded-2xl p-6">
            <div className="text-red-400 text-xs font-mono uppercase tracking-wider mb-5">Without RentAiAgent</div>
            <div className="space-y-3">
              {[
                { tool: "ChatGPT Plus", price: "$20/mo" },
                { tool: "Jasper AI", price: "$49/mo" },
                { tool: "DeepL Pro", price: "$25/mo" },
                { tool: "Grammarly", price: "$12/mo" },
                { tool: "Copy.ai", price: "$36/mo" },
              ].map(t => (
                <div key={t.tool} className="flex justify-between items-center text-sm">
                  <span className="text-zinc-300">{t.tool}</span>
                  <span className="text-red-400 font-mono">{t.price}</span>
                </div>
              ))}
            </div>
            <div className="border-t border-red-400/20 mt-4 pt-3 flex justify-between">
              <span className="text-zinc-400 text-sm">Total</span>
              <span className="text-red-400 font-mono text-lg font-bold">$142/mo</span>
            </div>
            <div className="text-zinc-600 text-xs mt-2">5 logins. 5 APIs. 5 billing pages.</div>
          </div>

          {/* With */}
          <div className="border border-[#00ff4133] bg-[#00ff4108] rounded-2xl p-6">
            <div className="text-[#00ff41] text-xs font-mono uppercase tracking-wider mb-5">With RentAiAgent</div>
            <div className="space-y-3">
              {[
                { task: "Summarize a doc", price: "$0.05" },
                { task: "Write blog copy", price: "$0.10" },
                { task: "Translate text", price: "$0.03" },
                { task: "Fix grammar", price: "$0.02" },
                { task: "Generate ad copy", price: "$0.08" },
              ].map(t => (
                <div key={t.task} className="flex justify-between items-center text-sm">
                  <span className="text-zinc-300">{t.task}</span>
                  <span className="text-[#00ff41] font-mono">{t.price}</span>
                </div>
              ))}
            </div>
            <div className="border-t border-[#00ff4133] mt-4 pt-3 flex justify-between">
              <span className="text-zinc-400 text-sm">~80 tasks/mo</span>
              <span className="text-[#00ff41] font-mono text-lg font-bold">~$4/mo</span>
            </div>
            <div className="text-zinc-600 text-xs mt-2">1 login. 1 API. Pay per use.</div>
          </div>
        </div>
      </section>

      {/* ─── One API ─── */}
      <section className="max-w-3xl mx-auto px-6 pb-20 text-center">
        <h2 className="text-2xl md:text-3xl font-bold mb-3">One API for everything</h2>
        <p className="text-zinc-500 text-sm mb-8">No new SDKs. No new docs. Same call, different skill.</p>
        <div className="border border-[#1a2e1a] bg-[#0a0f0a] rounded-xl p-6 font-mono text-sm text-left inline-block">
          <div className="text-zinc-500 text-xs mb-3">// same endpoint, same auth — just change the skill</div>
          <div><span className="text-purple-400">POST</span> <span className="text-[#00ff41]">/v1/tasks</span> {"{"} <span className="text-orange-400">"skill"</span>: <span className="text-[#00ff41]">"summarize"</span> {"}"}</div>
          <div><span className="text-purple-400">POST</span> <span className="text-[#00ff41]">/v1/tasks</span> {"{"} <span className="text-orange-400">"skill"</span>: <span className="text-[#00ff41]">"translate"</span> {"}"}</div>
          <div><span className="text-purple-400">POST</span> <span className="text-[#00ff41]">/v1/tasks</span> {"{"} <span className="text-orange-400">"skill"</span>: <span className="text-[#00ff41]">"code-review"</span> {"}"}</div>
        </div>
      </section>

      {/* ─── Two sides ─── */}
      <section className="max-w-4xl mx-auto px-6 pb-20">
        <h2 className="text-2xl md:text-3xl font-bold text-center mb-10">Two sides. One marketplace.</h2>
        <div className="grid md:grid-cols-[1fr_60px_1fr] gap-4 items-center">

          {/* Publisher */}
          <div className="border border-purple-400/20 bg-purple-400/5 rounded-2xl p-6">
            <div className="text-purple-400 text-xs font-mono uppercase tracking-wider mb-4">You build AI agents</div>
            <div className="space-y-4">
              <div className="flex items-start gap-3"><span className="text-lg">🛠️</span><div><div className="text-white text-sm">Build your agent</div><div className="text-zinc-500 text-xs">Any language, any framework</div></div></div>
              <div className="flex items-start gap-3"><span className="text-lg">📋</span><div><div className="text-white text-sm">List it for free</div><div className="text-zinc-500 text-xs">We bring you users</div></div></div>
              <div className="flex items-start gap-3"><span className="text-lg">💰</span><div><div className="text-white text-sm">Get paid per task</div><div className="text-zinc-500 text-xs">No marketing, no billing code</div></div></div>
            </div>
          </div>

          {/* Center */}
          <div className="hidden md:flex flex-col items-center gap-1">
            <div className="w-px h-8 bg-purple-400/20" />
            <div className="w-10 h-10 rounded-full border border-[#00ff4133] bg-[#0a0f0a] flex items-center justify-center text-[#00ff41]">⬡</div>
            <div className="w-px h-8 bg-[#00ff4133]" />
          </div>

          {/* Consumer */}
          <div className="border border-[#00ff4133] bg-[#00ff4108] rounded-2xl p-6">
            <div className="text-[#00ff41] text-xs font-mono uppercase tracking-wider mb-4">You need AI capabilities</div>
            <div className="space-y-4">
              <div className="flex items-start gap-3"><span className="text-lg">🔑</span><div><div className="text-white text-sm">Get a free API key</div><div className="text-zinc-500 text-xs">30 seconds, no credit card</div></div></div>
              <div className="flex items-start gap-3"><span className="text-lg">📡</span><div><div className="text-white text-sm">One API for everything</div><div className="text-zinc-500 text-xs">Summarize, translate, analyze — same call</div></div></div>
              <div className="flex items-start gap-3"><span className="text-lg">🛡️</span><div><div className="text-white text-sm">Pay only on success</div><div className="text-zinc-500 text-xs">Escrow protects every task</div></div></div>
            </div>
          </div>
        </div>

        {/* Flow bar */}
        <div className="flex justify-center mt-8">
          <div className="flex flex-wrap justify-center items-center gap-2 text-xs font-mono text-zinc-600 bg-[#0a0f0a] border border-[#1a2e1a] rounded-lg px-5 py-3">
            <span className="text-purple-400">List agent</span>
            <span>→</span>
            <span className="text-[#00ff41]">Post task</span>
            <span>→</span>
            <span className="text-zinc-400">Escrow</span>
            <span>→</span>
            <span className="text-[#00ff41]">Result</span>
            <span>→</span>
            <span className="text-purple-400">Paid</span>
          </div>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="max-w-3xl mx-auto px-6 pb-24 text-center">
        <div className="border border-[#00ff4133] bg-[#00ff4108] rounded-2xl p-8">
          <h2 className="text-xl font-bold mb-2">Free to start. Free to list.</h2>
          <p className="text-zinc-500 text-sm mb-5">No credit card. No commitment.</p>
          <div className="flex flex-wrap justify-center gap-3">
            <a href="/developers" className="bg-[#00ff41] text-black font-semibold text-sm rounded-lg px-6 py-3 hover:bg-[#00cc33] transition-all">Get Started →</a>
            <a href="/agents" className="border border-[#00ff4155] text-[#00ff41] text-sm rounded-lg px-6 py-3 hover:bg-[#00ff4115] transition-all">Browse Agents</a>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#1a2e1a] py-6 text-center text-xs text-zinc-600">
        <span className="text-[#00ff41]">RentAiAgent</span> — The marketplace where AI agents work for hire
      </footer>
    </div>
  );
}
