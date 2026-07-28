import { motion } from 'framer-motion';

export function Hero() {
  return (
    <header className="relative flex justify-center items-center min-h-[80vh] container mx-auto px-6 pt-24 pb-28 text-center bg-ragflow-bg overflow-hidden">
      
      {/* Background Star/Grid Effect from RAGFlow */}
      <div className="absolute inset-0 z-0 opacity-30 bg-[linear-gradient(to_right,#333333_1px,transparent_1px),linear-gradient(to_bottom,#333333_1px,transparent_1px)] bg-[size:100px_100px]"></div>
      
      {/* RAGFlow Inner Shadow/Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[150%] h-[600px] opacity-75 mix-blend-screen pointer-events-none">
        <div className="absolute inset-0 bg-ragflow-primary blur-[120px] rounded-full opacity-20"></div>
      </div>

      <div className="z-10 flex flex-col items-center">
        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="mx-auto text-center text-4xl md:text-6xl lg:text-7xl font-bold drop-shadow-glow text-balance mb-8"
        >
          <span className="text-white">Build a superior context layer for</span>{' '}
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-ragflow-primary to-ragflow-secondary whitespace-nowrap">
            AI agents
          </span>
        </motion.h1>
        
        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-lg md:text-xl text-ragflow-text-normal mb-12 max-w-3xl"
        >
          Empower your enterprise through the leading on-premise RAG engine, <br className="hidden md:block" />
          delivering reliable context via Master Agent routing and Hybrid GraphRAG.
        </motion.p>
        
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="relative inline-block group"
        >
          {/* Button Underglow identical to RAGFlow */}
          <div className="absolute -inset-1 bg-gradient-to-b from-ragflow-primary to-ragflow-secondary rounded-lg blur opacity-50 group-hover:opacity-100 transition duration-500"></div>
          <button className="relative px-9 py-3 rounded-lg bg-black text-white font-bold border border-transparent group-hover:border-ragflow-primary/50 transition-colors">
            Get Started
          </button>
        </motion.div>
      </div>
    </header>
  );
}
