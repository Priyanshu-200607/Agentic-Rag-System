import { motion } from 'framer-motion';
import { Route, BrainCircuit, ShieldCheck, DatabaseZap } from 'lucide-react';

const steps = [
  {
    icon: Route,
    title: "1. Intelligent Routing",
    desc: "A user submits a query. The Master Agent intercepts it and uses a localized LLM (e.g., Llama 3) to analyze the intent, deciding whether the question targets HR, IT, Finance, or a combination."
  },
  {
    icon: ShieldCheck,
    title: "2. Role-Based Access Control",
    desc: "Before any retrieval happens, the Master Agent checks the user's role. If an Intern asks a Finance question, the Master Agent strictly blocks it, ensuring zero data leakage."
  },
  {
    icon: BrainCircuit,
    title: "3. ReAct Tool-Use Agents",
    desc: "The query is routed to the authorized Department Agents. These agents act autonomously, choosing whether to use semantic vector search or graph traversal based on the question."
  },
  {
    icon: DatabaseZap,
    title: "4. Hybrid Retrieval & Synthesis",
    desc: "Agents retrieve facts from isolated ChromaDB collections and NetworkX graphs. The Master Agent then merges all department answers into one synthesized response."
  }
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 px-6 max-w-7xl mx-auto bg-ragflow-bg relative z-10 border-t border-ragflow-border">
      <div className="text-center mb-20 max-w-3xl mx-auto">
        <h2 className="font-display text-4xl md:text-5xl font-bold mb-6 text-white">How the Orchestrator Works</h2>
        <p className="text-gray-400 font-sans text-lg leading-relaxed">
          Unlike standard RAG pipelines that shove all documents into a single database, we use a multi-agent architecture to keep department knowledge isolated, secure, and highly accurate.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
        {steps.map((step, idx) => (
          <motion.div 
            key={idx}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: idx * 0.1 }}
            className="flex flex-col items-start bg-ragflow-card border border-ragflow-border p-8 rounded-2xl relative"
          >
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-ragflow-blue to-ragflow-green rounded-t-2xl opacity-50"></div>
            <div className="w-14 h-14 rounded-xl bg-gray-900 border border-gray-800 flex items-center justify-center mb-6">
              <step.icon className="w-7 h-7 text-ragflow-green" />
            </div>
            <h3 className="font-sans text-xl font-bold mb-4 text-white">{step.title}</h3>
            <p className="text-gray-400 font-sans text-sm leading-relaxed">{step.desc}</p>
          </motion.div>
        ))}
      </div>
    </section>
  );
}
