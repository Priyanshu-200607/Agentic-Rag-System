
import { Database } from 'lucide-react';

export function Navbar() {
  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0a0a0a]/80 backdrop-blur-lg border-b border-ragflow-border">
      <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-ragflow-blue to-ragflow-green flex items-center justify-center">
            <Database className="text-black w-6 h-6" />
          </div>
          <span className="font-display font-bold text-xl text-white tracking-wide">AgenticRAG</span>
        </div>
        
        <div className="hidden md:flex items-center gap-8">
          <a href="#how-it-works" className="text-gray-300 hover:text-white transition-colors text-sm font-semibold">How it Works</a>
          <a href="#features" className="text-gray-300 hover:text-white transition-colors text-sm font-semibold">Architecture</a>
          <a href="#security" className="text-gray-300 hover:text-white transition-colors text-sm font-semibold">Security</a>
          <a href="#pricing" className="text-gray-300 hover:text-white transition-colors text-sm font-semibold">Pricing</a>
        </div>

        <div className="flex items-center gap-4">
          <a href="https://github.com" target="_blank" rel="noreferrer" className="hidden md:block text-gray-300 hover:text-white transition-colors text-sm font-semibold">
            GitHub
          </a>
          <button className="px-5 py-2 rounded-lg text-black font-semibold text-sm bg-gradient-to-r from-ragflow-blue to-ragflow-green hover:opacity-90 transition-opacity">
            Get Started
          </button>
        </div>
      </div>
    </nav>
  );
}
