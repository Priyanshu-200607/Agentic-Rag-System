export function Pricing() {
  return (
    <section id="pricing" className="py-32 px-6 max-w-6xl mx-auto bg-ragflow-bg">
      <div className="text-center mb-20 max-w-2xl mx-auto">
        <h2 className="font-display text-4xl md:text-5xl font-bold mb-6 text-white">Transparent Licensing</h2>
        <p className="text-gray-400 font-sans text-lg">Deploy entirely on-premise. No hidden costs. No per-token charges.</p>
      </div>

      <div className="grid md:grid-cols-2 gap-8 relative max-w-4xl mx-auto">
        
        {/* Open Source Tier */}
        <div className="p-10 rounded-2xl border border-gray-800 bg-[#111] flex flex-col">
          <div className="mb-6">
            <h3 className="font-sans text-2xl font-bold mb-2 text-white">Community</h3>
            <p className="text-gray-400 font-sans text-sm">For developers and small teams.</p>
          </div>
          <div className="text-5xl font-display font-bold mb-10 text-white">Free</div>
          
          <ul className="space-y-4 mb-12 text-gray-300 font-sans text-sm flex-1">
            <li className="flex items-center gap-3"><span className="text-ragflow-green text-lg font-bold">✓</span> Full Source Code</li>
            <li className="flex items-center gap-3"><span className="text-ragflow-green text-lg font-bold">✓</span> Hybrid GraphRAG</li>
            <li className="flex items-center gap-3"><span className="text-ragflow-green text-lg font-bold">✓</span> Basic RBAC</li>
            <li className="flex items-center gap-3 text-gray-600"><span className="text-gray-600 text-lg font-bold">−</span> No SSO Integration</li>
          </ul>
          
          <button className="w-full py-3.5 rounded-lg border border-gray-600 hover:bg-gray-800 transition-colors font-sans font-semibold text-white">
            View on GitHub
          </button>
        </div>

        {/* Enterprise Tier */}
        <div className="p-10 rounded-2xl border border-ragflow-blue bg-gradient-to-b from-[#111] to-[#0a1520] relative flex flex-col shadow-[0_0_30px_rgba(66,182,255,0.15)]">
          <div className="absolute top-0 right-8 bg-ragflow-blue text-black text-xs font-bold px-4 py-1.5 rounded-b-lg tracking-wider uppercase">Enterprise</div>
          
          <div className="mb-6 mt-2">
            <h3 className="font-sans text-2xl font-bold mb-2 text-white">Commercial</h3>
            <p className="text-gray-400 font-sans text-sm">For strictly regulated environments.</p>
          </div>
          <div className="text-5xl font-display font-bold mb-10 text-white">Custom</div>
          
          <ul className="space-y-4 mb-12 text-white font-sans text-sm flex-1">
            <li className="flex items-center gap-3"><span className="text-ragflow-blue text-lg font-bold">✓</span> Active Directory / SSO</li>
            <li className="flex items-center gap-3"><span className="text-ragflow-blue text-lg font-bold">✓</span> Advanced Telemetry Logs</li>
            <li className="flex items-center gap-3"><span className="text-ragflow-blue text-lg font-bold">✓</span> Custom LangGraph Tooling</li>
            <li className="flex items-center gap-3"><span className="text-ragflow-blue text-lg font-bold">✓</span> Dedicated Support SLA</li>
          </ul>
          
          <button className="w-full py-3.5 rounded-lg bg-ragflow-blue text-black hover:opacity-90 transition-opacity font-sans font-semibold">
            Contact Sales
          </button>
        </div>

      </div>
    </section>
  );
}
