export function Workflow() {
  return (
    <section id="security" className="py-32 px-6 bg-[#0a0a0a] w-full border-t border-ragflow-border">
      <div className="max-w-7xl mx-auto">
        <div className="grid md:grid-cols-2 gap-16 items-center">
          
          <div>
             <h2 className="font-display text-4xl font-bold mb-6 text-white">
              Granular <span className="text-red-400">RBAC</span> Orchestration
            </h2>
            <p className="text-gray-300 font-sans text-lg mb-6 leading-relaxed">
              In an enterprise environment, security cannot be an afterthought. 
            </p>
            <p className="text-gray-400 font-sans text-base leading-relaxed mb-8">
              Access control is enforced at the **Orchestrator Level**. Before a query ever reaches a database, the Master Agent verifies the user's role. If an unauthorized user attempts to query restricted departmental data (e.g., an Intern asking about Finance payroll), the path is strictly blocked at the routing layer. Data isolation is physically guaranteed.
            </p>
            <button className="px-6 py-3 rounded text-white font-sans font-semibold bg-gray-900 border border-gray-700 hover:bg-gray-800 transition-colors">
              Read Security Whitepaper
            </button>
          </div>

          <div className="w-full bg-ragflow-card border border-ragflow-border rounded-2xl p-6 shadow-2xl relative overflow-hidden">
            <svg className="w-full h-auto" viewBox="0 0 600 400" fill="none">
              
              {/* User Block */}
              <rect x="20" y="160" width="120" height="80" rx="8" className="fill-[#1a1a1a] stroke-ragflow-border stroke-[2px]" />
              <text x="80" y="195" className="fill-white text-base font-sans font-bold" textAnchor="middle">User Request</text>
              <text x="80" y="215" className="fill-gray-400 text-xs font-mono" textAnchor="middle">Role: INTERN</text>

              {/* Path to Master Agent */}
              <path d="M 140 200 L 240 200" className="stroke-ragflow-blue stroke-[3px]" />
              <circle cx="190" cy="200" r="4" className="fill-ragflow-blue">
                 <animate attributeName="cx" values="140; 240" dur="1.5s" repeatCount="indefinite" />
              </circle>

              {/* Master Agent */}
              <rect x="240" y="130" width="140" height="140" rx="12" className="fill-[#0f151c] stroke-ragflow-blue stroke-[2px]" />
              <text x="310" y="185" className="fill-white text-lg font-sans font-bold" textAnchor="middle">Master Agent</text>
              <text x="310" y="205" className="fill-ragflow-blue text-xs font-mono font-bold" textAnchor="middle">RBAC Validator</text>

              {/* Allowed Path */}
              <path d="M 380 160 L 460 100" className="stroke-ragflow-green stroke-[3px]" />
              <circle cx="430" cy="122" r="14" className="fill-[#111] stroke-ragflow-green stroke-[2px]" />
              <text x="430" y="127" className="fill-ragflow-green text-sm font-bold" textAnchor="middle">✓</text>
              
              <rect x="460" y="60" width="120" height="70" rx="8" className="fill-[#1a1a1a] stroke-ragflow-green stroke-[2px]" />
              <text x="520" y="95" className="fill-white font-sans text-sm font-bold" textAnchor="middle">HR Agent</text>
              <text x="520" y="115" className="fill-gray-400 text-[10px] font-mono" textAnchor="middle">Allowed</text>

              {/* Blocked Path */}
              <path d="M 380 240 L 460 300" className="stroke-red-500 stroke-[3px]" strokeDasharray="6 6" />
              <circle cx="430" cy="278" r="14" className="fill-[#111] stroke-red-500 stroke-[2px]" />
              <text x="430" y="283" className="fill-red-500 text-sm font-bold" textAnchor="middle">✕</text>
              
              <rect x="460" y="270" width="120" height="70" rx="8" className="fill-[#110505] stroke-red-900 stroke-[2px]" />
              <text x="520" y="305" className="fill-gray-500 font-sans text-sm font-bold" textAnchor="middle">Finance Agent</text>
              <text x="520" y="325" className="fill-red-500 text-[10px] font-mono font-bold" textAnchor="middle">BLOCKED</text>

            </svg>
          </div>

        </div>
      </div>
    </section>
  );
}
