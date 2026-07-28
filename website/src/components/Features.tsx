

export function Features() {
  return (
    <main className="relative z-10 container mx-auto px-6 bg-ragflow-bg pb-32">
      <section className="grid grid-cols-1 md:grid-cols-2 gap-6" aria-label="Features">
        
        {/* Feature 1: Adaptive Extraction (RAGFlow ETL Style) */}
        <article className="flex flex-col bg-ragflow-standard border border-ragflow-border rounded-xl p-8 hover:border-ragflow-border/80 transition-colors group relative overflow-hidden">
          {/* Card Hover Underglow */}
          <div className="absolute -inset-[1px] bg-gradient-to-b from-ragflow-primary to-ragflow-secondary rounded-xl opacity-0 group-hover:opacity-10 transition duration-500 pointer-events-none"></div>
          
          <header>
            <h2 className="text-2xl font-bold mb-4">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-ragflow-primary to-ragflow-secondary">
                Hardware-Aware Extraction
              </span>
            </h2>
          </header>
          <p className="text-ragflow-text-muted text-base mb-8">
            Harness our built-in Resource Manager to automatically switch between fast REBEL-based graph extraction on consumer GPUs and high-quality LLM-based extraction on enterprise hardware.
          </p>
          
          {/* SVG Diagram Bottom */}
          <div className="w-full aspect-video mt-auto border border-ragflow-border rounded-lg bg-[#080808] flex items-center justify-center p-4 relative">
             <svg viewBox="0 0 400 200" fill="none" className="w-full h-full">
                {/* Simulated RAGFlow animated ETL path */}
                <rect x="20" y="80" width="80" height="40" rx="4" className="fill-[#1a1a1a] stroke-ragflow-border stroke-2" />
                <text x="60" y="105" className="fill-gray-400 text-xs font-bold" textAnchor="middle">Documents</text>

                <path d="M 100 100 L 180 100" className="stroke-ragflow-primary stroke-2" strokeDasharray="4 4">
                  <animate attributeName="stroke-dashoffset" values="8;0" dur="1s" repeatCount="indefinite" />
                </path>

                <rect x="180" y="60" width="100" height="80" rx="8" className="fill-ragflow-standard stroke-ragflow-primary stroke-2" />
                <text x="230" y="95" className="fill-white text-sm font-bold" textAnchor="middle">Resource Mgr</text>
                <text x="230" y="115" className="fill-ragflow-secondary text-[10px]" textAnchor="middle">Adaptive VRAM</text>

                <path d="M 280 100 L 320 100" className="stroke-ragflow-border stroke-2" />
                
                <rect x="320" y="80" width="60" height="40" rx="4" className="fill-[#1a1a1a] stroke-gray-600 stroke-2" />
                <text x="350" y="105" className="fill-gray-300 text-xs font-bold" textAnchor="middle">Graphs</text>
             </svg>
          </div>
        </article>

        {/* Feature 2: Hybrid Search */}
        <article className="flex flex-col bg-ragflow-standard border border-ragflow-border rounded-xl p-8 hover:border-ragflow-border/80 transition-colors group relative overflow-hidden">
          <div className="absolute -inset-[1px] bg-gradient-to-b from-ragflow-primary to-ragflow-secondary rounded-xl opacity-0 group-hover:opacity-10 transition duration-500 pointer-events-none"></div>
          
          <header>
            <h2 className="text-2xl font-bold mb-4">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-ragflow-primary to-ragflow-secondary">
                High-Precision hybrid search
              </span>
            </h2>
          </header>
          <p className="text-ragflow-text-muted text-base mb-8">
            Combine ChromaDB vector semantics with NetworkX / SQLite relational knowledge graphs. Eliminate the blind spots of plain vector search.
          </p>
          
          <div className="w-full aspect-video mt-auto border border-ragflow-border rounded-lg bg-[#080808] flex items-center justify-center p-4">
            <svg viewBox="0 0 400 200" fill="none" className="w-full h-full">
                <circle cx="150" cy="100" r="50" className="stroke-ragflow-primary stroke-[3px] fill-transparent" />
                <text x="150" y="105" className="fill-ragflow-primary text-xs font-bold" textAnchor="middle">Vector DB</text>
                
                <circle cx="250" cy="100" r="50" className="stroke-ragflow-secondary stroke-[3px] fill-transparent" />
                <text x="250" y="105" className="fill-ragflow-secondary text-xs font-bold" textAnchor="middle">Graph DB</text>

                <path d="M 185 80 L 215 80" className="stroke-white stroke-2" />
                <path d="M 185 120 L 215 120" className="stroke-white stroke-2" />
                
                <rect x="170" y="85" width="60" height="30" rx="15" className="fill-white" />
                <text x="200" y="104" className="fill-black text-[10px] font-bold" textAnchor="middle">Hybrid</text>
            </svg>
          </div>
        </article>

        {/* Feature 3: RBAC Orchestration */}
        <article className="flex flex-col bg-ragflow-standard border border-ragflow-border rounded-xl p-8 hover:border-ragflow-border/80 transition-colors group relative overflow-hidden">
          <div className="absolute -inset-[1px] bg-gradient-to-b from-ragflow-primary to-ragflow-secondary rounded-xl opacity-0 group-hover:opacity-10 transition duration-500 pointer-events-none"></div>
          
          <header>
            <h2 className="text-2xl font-bold mb-4">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-ragflow-primary to-ragflow-secondary">
                Airtight RBAC Security
              </span>
            </h2>
          </header>
          <p className="text-ragflow-text-muted text-base mb-8">
            Access control is enforced at the orchestrator level. Users physically cannot query departmental data they aren't explicitly authorized to see.
          </p>
          
          <div className="w-full aspect-video mt-auto border border-ragflow-border rounded-lg bg-[#080808] flex items-center justify-center p-4">
            <svg viewBox="0 0 400 200" fill="none" className="w-full h-full">
                <rect x="50" y="80" width="80" height="40" rx="4" className="fill-[#1a1a1a] stroke-ragflow-border stroke-2" />
                <text x="90" y="105" className="fill-white text-xs font-bold" textAnchor="middle">Intern</text>

                <path d="M 130 100 L 200 100" className="stroke-ragflow-primary stroke-[3px]" />
                
                <rect x="200" y="60" width="80" height="80" rx="8" className="fill-ragflow-standard stroke-ragflow-primary stroke-2" />
                <text x="240" y="95" className="fill-white text-xs font-bold" textAnchor="middle">Master Agent</text>
                <text x="240" y="115" className="fill-ragflow-primary text-[9px]" textAnchor="middle">Validator</text>

                <path d="M 280 80 L 320 60" className="stroke-ragflow-secondary stroke-[3px]" />
                <circle cx="300" cy="70" r="8" className="fill-[#111] stroke-ragflow-secondary stroke-2" />
                <text x="300" y="74" className="fill-ragflow-secondary text-[10px] font-bold" textAnchor="middle">✓</text>
                <rect x="320" y="40" width="60" height="40" rx="4" className="fill-[#1a1a1a] stroke-ragflow-secondary stroke-2" />
                <text x="350" y="65" className="fill-white text-[10px] font-bold" textAnchor="middle">HR DB</text>

                <path d="M 280 120 L 320 140" className="stroke-red-500 stroke-[3px]" strokeDasharray="4 4" />
                <circle cx="300" cy="130" r="8" className="fill-[#111] stroke-red-500 stroke-2" />
                <text x="300" y="134" className="fill-red-500 text-[10px] font-bold" textAnchor="middle">✕</text>
                <rect x="320" y="120" width="60" height="40" rx="4" className="fill-[#080808] stroke-red-900 stroke-2" />
                <text x="350" y="145" className="fill-gray-600 text-[10px] font-bold" textAnchor="middle">Finance</text>
            </svg>
          </div>
        </article>

        {/* Feature 4: ReAct Routing */}
        <article className="flex flex-col bg-ragflow-standard border border-ragflow-border rounded-xl p-8 hover:border-ragflow-border/80 transition-colors group relative overflow-hidden">
          <div className="absolute -inset-[1px] bg-gradient-to-b from-ragflow-primary to-ragflow-secondary rounded-xl opacity-0 group-hover:opacity-10 transition duration-500 pointer-events-none"></div>
          
          <header>
            <h2 className="text-2xl font-bold mb-4">
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-ragflow-primary to-ragflow-secondary">
                Dynamic Agentic Routing
              </span>
            </h2>
          </header>
          <p className="text-ragflow-text-muted text-base mb-8">
            No hardcoded `/chat/hr` endpoints. The Master Agent evaluates intent, splits cross-department queries, and merges synthesized responses autonomously.
          </p>
          
          <div className="w-full aspect-video mt-auto border border-ragflow-border rounded-lg bg-[#080808] flex items-center justify-center p-4">
             <svg viewBox="0 0 400 200" fill="none" className="w-full h-full">
                <rect x="40" y="80" width="80" height="40" rx="4" className="fill-[#1a1a1a] stroke-ragflow-border stroke-2" />
                <text x="80" y="105" className="fill-white text-[10px] font-bold" textAnchor="middle">"HR & IT impact?"</text>

                <path d="M 120 100 L 160 100" className="stroke-ragflow-primary stroke-2" strokeDasharray="4 4">
                  <animate attributeName="stroke-dashoffset" values="8;0" dur="1s" repeatCount="indefinite" />
                </path>

                <rect x="160" y="70" width="80" height="60" rx="8" className="fill-ragflow-standard stroke-ragflow-primary stroke-2" />
                <text x="200" y="100" className="fill-white text-xs font-bold" textAnchor="middle">Router</text>

                <path d="M 240 85 L 280 65" className="stroke-ragflow-secondary stroke-2" />
                <path d="M 240 115 L 280 135" className="stroke-ragflow-secondary stroke-2" />

                <rect x="280" y="45" width="80" height="40" rx="4" className="fill-ragflow-standard stroke-ragflow-secondary stroke-2" />
                <text x="320" y="70" className="fill-white text-[10px] font-bold" textAnchor="middle">HR Agent</text>

                <rect x="280" y="115" width="80" height="40" rx="4" className="fill-ragflow-standard stroke-ragflow-secondary stroke-2" />
                <text x="320" y="140" className="fill-white text-[10px] font-bold" textAnchor="middle">IT Agent</text>
             </svg>
          </div>
        </article>

      </section>
    </main>
  );
}
