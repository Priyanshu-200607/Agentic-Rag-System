import { useEffect, useRef } from 'react';

function App() {
  const heroRef = useRef<HTMLElement>(null);
  const heroGlowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Scroll Reveal Animation
    function reveal() {
      var reveals = document.querySelectorAll(".reveal");
      for (var i = 0; i < reveals.length; i++) {
        var windowHeight = window.innerHeight;
        var elementTop = reveals[i].getBoundingClientRect().top;
        var elementVisible = 150;
        if (elementTop < windowHeight - elementVisible) {
          reveals[i].classList.add("active");
        }
      }
    }

    window.addEventListener("scroll", reveal);
    reveal();

    // Simple mouse tracking for hero glow
    const handleMouseMove = (e: MouseEvent) => {
      if (heroGlowRef.current) {
        const x = (e.clientX / window.innerWidth) * 20 - 10;
        const y = (e.clientY / window.innerHeight) * 20 - 10;
        heroGlowRef.current.style.transform = `translate(calc(-50% + ${x}px), ${y}px)`;
      }
    };

    const heroSection = heroRef.current;
    if (heroSection) {
      heroSection.addEventListener('mousemove', handleMouseMove);
    }

    return () => {
      window.removeEventListener("scroll", reveal);
      if (heroSection) {
        heroSection.removeEventListener('mousemove', handleMouseMove);
      }
    };
  }, []);

  return (
    <div className="font-body-md selection:bg-primary/30 selection:text-primary">
      {/* Top Navigation Bar */}
      <nav className="fixed top-0 w-full z-50 glass-nav border-b border-outline-variant/30 h-20">
        <div className="flex justify-between items-center px-margin-desktop h-full max-w-container-max mx-auto">
          <div className="flex items-center gap-stack-md">
            <img alt="AgenticRAG Logo" className="h-10 w-10 object-contain" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBcYWF4-dmV6XSJxVTyCELz38bBICSIVxuIHFaNSWtqhB7oFxd0YOhR14j9KISWPb7ymD_v0AwD1nWU0OGPo-Bp2Vbk7i3-KgvSrNfyVOiFBQ4gBOkFazRBNPfHRxx2nPc5UK9PdAhYOqtRwuAKdkDfekYqg2aBggnCXheXqavp5caEwSMGxnx-rLg5yYNDJzb8W5Wti_9a4aQyFVB7jmYNxN8posh1QyD6AINH0CuQY6H_80I9EIyTdGwzZt40IcpeXFIi7PeAig"/>
            <span className="font-display-lg text-headline-md font-bold text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary">AgenticRAG</span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a className="text-on-surface-variant hover:text-on-surface transition-colors font-body-md" href="#solutions">Solutions</a>
            <a className="text-on-surface-variant hover:text-on-surface transition-colors font-body-md" href="#workflow">Workflow</a>
            <a className="text-on-surface-variant hover:text-on-surface transition-colors font-body-md" href="#features">Features</a>
            <a className="text-on-surface-variant hover:text-on-surface transition-colors font-body-md" href="#pricing">Pricing</a>
          </div>
          <div className="flex items-center gap-stack-md">
            <button className="hidden sm:block text-on-surface-variant hover:text-on-surface transition-all duration-300 font-body-md">Login</button>
            <button className="bg-primary hover:opacity-90 text-on-primary font-bold px-6 py-2.5 rounded-sm transition-all active:scale-95 shadow-lg shadow-primary/20">Get Started</button>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <header ref={heroRef} className="relative pt-40 pb-32 overflow-hidden px-margin-mobile md:px-margin-desktop">
        <div ref={heroGlowRef} className="absolute top-0 left-1/2 -translate-x-1/2 w-[140%] h-[120%] hero-glow -z-10 pointer-events-none"></div>
        <div className="max-w-container-max mx-auto text-center relative z-10">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-surface-container-low border border-outline-variant/30 mb-stack-lg reveal">
            <span className="w-2 h-2 rounded-full bg-secondary animate-pulse"></span>
            <span className="text-label-sm font-label-sm text-on-surface-variant tracking-wider uppercase">Enterprise Retrieval Framework v2.4</span>
          </div>
          <h1 className="font-display-lg text-display-lg-mobile md:text-[4rem] mb-stack-md max-w-4xl mx-auto reveal" style={{ transitionDelay: '100ms' }}>
            Build a <span className="gradient-text">superior context layer</span> for AI agents
          </h1>
          <p className="text-on-surface-variant font-body-lg text-body-lg max-w-2xl mx-auto mb-stack-lg reveal" style={{ transitionDelay: '200ms' }}>
            Orchestrate complex document extraction, hybrid retrieval, and hardware-aware scaling with the only framework designed for production agentic workflows.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-stack-md reveal" style={{ transitionDelay: '300ms' }}>
            <button className="w-full sm:w-auto bg-gradient-to-r from-primary to-secondary text-on-primary font-bold px-10 py-4 rounded-sm underglow-primary hover:opacity-90 transition-all active:scale-95">
              Get Started Free
            </button>
            <button className="w-full sm:w-auto flex items-center justify-center gap-2 border border-outline-variant/50 text-on-surface hover:bg-surface-container-low px-10 py-4 rounded-sm transition-all">
              <span className="material-symbols-outlined text-[20px]">play_circle</span>
              Watch Demo
            </button>
          </div>

          {/* Dashboard Preview Mockup */}
          <div className="mt-20 relative reveal" style={{ transitionDelay: '400ms' }}>
            <div className="mx-auto max-w-5xl rounded-lg border border-outline-variant/30 bg-surface-container-lowest overflow-hidden shadow-2xl">
              <div className="h-10 bg-surface-container border-b border-outline-variant/20 flex items-center px-4 gap-2">
                <div className="w-3 h-3 rounded-full bg-error/40"></div>
                <div className="w-3 h-3 rounded-full bg-primary/40"></div>
                <div className="w-3 h-3 rounded-full bg-secondary/40"></div>
              </div>
              <div className="p-8 aspect-video bg-[#0d0d0d] flex items-center justify-center text-on-surface-variant font-code-snippet">
                <div className="w-full h-full flex flex-col gap-4">
                  <div className="h-8 w-1/3 bg-surface-container-high rounded animate-pulse"></div>
                  <div className="grid grid-cols-3 gap-4 h-full">
                    <div className="bg-surface-container-low rounded-lg p-4 flex flex-col gap-3">
                      <div className="h-4 w-full bg-outline-variant/20 rounded"></div>
                      <div className="h-4 w-2/3 bg-outline-variant/20 rounded"></div>
                      <div className="mt-auto h-24 bg-gradient-to-t from-primary/10 to-transparent rounded"></div>
                    </div>
                    <div className="col-span-2 bg-surface-container-low rounded-lg p-6 flex flex-col gap-4">
                      <div className="flex justify-between items-center">
                        <div className="h-6 w-32 bg-outline-variant/40 rounded"></div>
                        <div className="h-8 w-8 bg-secondary/20 rounded-full"></div>
                      </div>
                      <div className="space-y-3">
                        <div className="h-4 w-full bg-outline-variant/10 rounded"></div>
                        <div className="h-4 w-[90%] bg-outline-variant/10 rounded"></div>
                        <div className="h-4 w-[95%] bg-outline-variant/10 rounded"></div>
                        <div className="h-4 w-[40%] bg-outline-variant/10 rounded"></div>
                      </div>
                      <div className="mt-auto flex gap-4">
                        <div className="h-10 w-24 bg-primary/30 rounded"></div>
                        <div className="h-10 w-24 border border-outline-variant/30 rounded"></div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* How it Works Section */}
      <section className="py-stack-lg px-margin-mobile md:px-margin-desktop bg-surface-container-lowest" id="workflow">
        <div className="max-w-container-max mx-auto">
          <div className="mb-20 reveal">
            <h2 className="font-display-lg text-headline-md md:text-display-lg mb-4">Precision Engineering for Context</h2>
            <p className="text-on-surface-variant max-w-xl text-body-md">Engineered to bridge the gap between static enterprise data and dynamic LLM orchestration.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-stack-md">
            <div className="card-glow p-8 bg-surface rounded-xl border border-outline-variant/20 flex flex-col gap-4 reveal" style={{ transitionDelay: '50ms' }}>
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary">route</span>
              </div>
              <h3 className="font-headline-md text-headline-md">1. Routing</h3>
              <p className="text-on-surface-variant text-body-md">Intelligently route queries to the most relevant data silos based on semantic intent.</p>
              <div className="mt-4 h-1 w-full bg-outline-variant/10 rounded-full overflow-hidden">
                <div className="h-full w-1/4 bg-primary rounded-full"></div>
              </div>
            </div>
            <div className="card-glow p-8 bg-surface rounded-xl border border-outline-variant/20 flex flex-col gap-4 reveal" style={{ transitionDelay: '150ms' }}>
              <div className="w-12 h-12 rounded-lg bg-secondary/10 flex items-center justify-center">
                <span className="material-symbols-outlined text-secondary">admin_panel_settings</span>
              </div>
              <h3 className="font-headline-md text-headline-md">2. RBAC</h3>
              <p className="text-on-surface-variant text-body-md">Embed complex permission structures directly into the retrieval flow to prevent leaks.</p>
              <div className="mt-4 h-1 w-full bg-outline-variant/10 rounded-full overflow-hidden">
                <div className="h-full w-2/4 bg-secondary rounded-full"></div>
              </div>
            </div>
            <div className="card-glow p-8 bg-surface rounded-xl border border-outline-variant/20 flex flex-col gap-4 reveal" style={{ transitionDelay: '250ms' }}>
              <div className="w-12 h-12 rounded-lg bg-tertiary/10 flex items-center justify-center">
                <span className="material-symbols-outlined text-tertiary">psychology</span>
              </div>
              <h3 className="font-headline-md text-headline-md">3. ReAct Agents</h3>
              <p className="text-on-surface-variant text-body-md">Deploy native ReAct loops that allow agents to self-correct retrieval and iterate.</p>
              <div className="mt-4 h-1 w-full bg-outline-variant/10 rounded-full overflow-hidden">
                <div className="h-full w-3/4 bg-tertiary rounded-full"></div>
              </div>
            </div>
            <div className="card-glow p-8 bg-surface rounded-xl border border-outline-variant/20 flex flex-col gap-4 reveal" style={{ transitionDelay: '350ms' }}>
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                <span className="material-symbols-outlined text-primary">hub</span>
              </div>
              <h3 className="font-headline-md text-headline-md">4. Hybrid Retrieval</h3>
              <p className="text-on-surface-variant text-body-md">Fuse semantic vector search with keyword and knowledge graph signals for recall.</p>
              <div className="mt-4 h-1 w-full bg-outline-variant/10 rounded-full overflow-hidden">
                <div className="h-full w-full bg-gradient-to-r from-primary to-secondary rounded-full"></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Bento Grid */}
      <section className="py-stack-lg px-margin-mobile md:px-margin-desktop relative overflow-hidden" id="features">
        <div className="max-w-container-max mx-auto relative z-10">
          <div className="mb-16 text-center reveal">
            <h2 className="font-display-lg text-headline-md md:text-display-lg mb-4">Unrivaled Infrastructure</h2>
            <p className="text-on-surface-variant max-w-2xl mx-auto text-body-md">Performance without compromise. Secure by default. Scale to infinity.</p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-gutter">
            <div className="card-glow group bg-[#111] border border-outline-variant/20 rounded-xl overflow-hidden flex flex-col reveal" style={{ transitionDelay: '100ms' }}>
              <div className="p-8">
                <div className="flex items-center gap-3 mb-4">
                  <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>memory</span>
                  <h4 className="font-headline-md text-headline-md">Hardware-Aware Extraction</h4>
                </div>
                <p className="text-on-surface-variant text-body-md mb-8">Automatically adjust document parsing pipelines based on available VRAM and compute nodes. No more OOM errors in production.</p>
              </div>
              <div className="mt-auto p-4 bg-surface-container-lowest/50 border-t border-outline-variant/10">
                <img alt="Hardware-Aware Extraction Diagram" className="w-full h-auto rounded opacity-80 group-hover:opacity-100 transition-opacity" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBASkQRKLoblK85RTZ3VoGK8SiaNCWJen0UKDCl7Y-T6ID_sSZN934cfrawlOVJb0-R5Jax3y1WanL8pTRHm2YcPkm6fmbeqqGRxVgfri1gtg7idhVTbgrUbIlFIyNxE8e3YZ4tqn5588QCJ5-ALGMXx2yNDM6FbYPTJgrYePdPh43HWxXsa9EXEU5SULhU73uTadNkAEBD7EqUCOKxdZ39wCOyOgBPq27rqLR2SrhHKbKEvT-x7aV0C0QVaM-gHG-hb0HwQxhDQg"/>
              </div>
            </div>
            <div className="card-glow group bg-[#111] border border-outline-variant/20 rounded-xl overflow-hidden flex flex-col reveal" style={{ transitionDelay: '200ms' }}>
              <div className="p-8">
                <div className="flex items-center gap-3 mb-4">
                  <span className="material-symbols-outlined text-secondary" style={{ fontVariationSettings: "'FILL' 1" }}>manage_search</span>
                  <h4 className="font-headline-md text-headline-md">High-Precision Hybrid Search</h4>
                </div>
                <p className="text-on-surface-variant text-body-md mb-8">Merge Vector DBs and Graph structures into a unified semantic map. Perfect for complex cross-entity queries.</p>
              </div>
              <div className="mt-auto p-4 bg-surface-container-lowest/50 border-t border-outline-variant/10">
                <img alt="Hybrid Search Diagram" className="w-full h-auto rounded opacity-80 group-hover:opacity-100 transition-opacity" src="https://lh3.googleusercontent.com/aida-public/AB6AXuDnYbAVmOS7qs9iZM8J8N6XGMpum8ULK541TPEMjcxGa47eqh0bbcNA_Q1_yRFvY7HKccZ7dIPNm5-BRRqGgUeH_6kNnxNXAUgkIy5k2tcUM9bfDFYh21VnyBzgmlxlRAiSIQAEQhVRSHTEVpGulsLB__2BCP5PzjwyJ9SL572tqQXPfvcDKzfRifuOEjqjJGYaN-OejxiGy-yK-WLt6_haNCM0nS-Sye-aM67V-XJfXMsqfg6zdL-8slKXuAlwQqdvkT_WrWcRfQ"/>
              </div>
            </div>
            <div className="card-glow group bg-[#111] border border-outline-variant/20 rounded-xl overflow-hidden flex flex-col reveal" style={{ transitionDelay: '300ms' }}>
              <div className="p-8">
                <div className="flex items-center gap-3 mb-4">
                  <span className="material-symbols-outlined text-tertiary" style={{ fontVariationSettings: "'FILL' 1" }}>security</span>
                  <h4 className="font-headline-md text-headline-md">Airtight RBAC Security</h4>
                </div>
                <p className="text-on-surface-variant text-body-md mb-8">Role-based access control at the document and chunk level. Ensure LLMs never see data they shouldn't.</p>
              </div>
              <div className="mt-auto p-4 bg-surface-container-lowest/50 border-t border-outline-variant/10">
                <img alt="RBAC Security Diagram" className="w-full h-auto rounded opacity-80 group-hover:opacity-100 transition-opacity" src="https://lh3.googleusercontent.com/aida-public/AB6AXuD7X7B62f1AsGlWpjELvzmDbGcbLNyM43nRvXn7uS3pZqrLytQbSN9u40OIqrP1pUIwMrsjVor46Df1MdWo4Sd4Kon9E6PiaGOIZIH3j-Z2xysRgG2mGisoMBw3Vt3D_Y9pT9MXHhgKVfDur73riNRqRJOzCIp4lD-_VPRHX7EsrUSkc4BIO03dotWSUKk-05OSDjGvvI3N1WSFmOw67JG3DFln-_oGb_Qmwrz1migCacrRo8En1YunzFaq9uUrPzbu4AtbCc78Fg"/>
              </div>
            </div>
            <div className="card-glow group bg-[#111] border border-outline-variant/20 rounded-xl overflow-hidden flex flex-col reveal" style={{ transitionDelay: '400ms' }}>
              <div className="p-8">
                <div className="flex items-center gap-3 mb-4">
                  <span className="material-symbols-outlined text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>alt_route</span>
                  <h4 className="font-headline-md text-headline-md">Dynamic Agentic Routing</h4>
                </div>
                <p className="text-on-surface-variant text-body-md mb-8">Router agents that classify user intent and dispatch to specialized sub-agents with surgical precision.</p>
              </div>
              <div className="mt-auto p-4 bg-surface-container-lowest/50 border-t border-outline-variant/10">
                <img alt="Agentic Routing Diagram" className="w-full h-auto rounded opacity-80 group-hover:opacity-100 transition-opacity" src="https://lh3.googleusercontent.com/aida-public/AB6AXuCOFXjouY5FoOVnweFSVsIrmMufA349H-XIszuna2ZW1DFiIJdaQfZkFpYw0GSoXYp1r4tDuOJD1-Ypdm9IrsKTvSvtL-Hg9Ct0WCn96otYQMtMaVUFPLuX5aIr_l2GWqN6d_AqZpRwGdK9HzSIIovRp1nBkG2DhsmJWl7rV9aZ0xuZC0P32frQ8Jw1M7d1rxZR5huWCLqTQd0TDnOt01I0xPmKDx0ZNvjzUDN9lbrpmTyPjCk-IBEVR7KZwbbtLJKCJJ12nsJSXg"/>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="py-stack-lg px-margin-mobile md:px-margin-desktop bg-surface-container-lowest relative overflow-hidden" id="pricing">
        <div className="max-w-container-max mx-auto text-center reveal">
          <h2 className="font-display-lg text-headline-md md:text-display-lg mb-4">Scale with Your Needs</h2>
          <p className="text-on-surface-variant mb-16 text-body-md">Transparent pricing for teams of all sizes.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-stack-lg max-w-4xl mx-auto">
            <div className="bg-surface border border-outline-variant/20 p-10 rounded-xl flex flex-col items-center text-center">
              <span className="px-4 py-1 rounded-full bg-outline-variant/10 text-label-sm font-label-sm text-on-surface-variant mb-6">OPEN SOURCE</span>
              <h3 className="font-headline-md text-headline-md mb-2">Community</h3>
              <div className="mb-8">
                <span className="text-4xl font-bold">$0</span>
                <span className="text-on-surface-variant">/forever</span>
              </div>
              <ul className="space-y-4 mb-10 text-on-surface-variant text-left w-full">
                <li className="flex items-center gap-3"><span className="material-symbols-outlined text-secondary text-sm">check_circle</span> Unlimited agents</li>
                <li className="flex items-center gap-3"><span className="material-symbols-outlined text-secondary text-sm">check_circle</span> Core retrieval engine</li>
                <li className="flex items-center gap-3"><span className="material-symbols-outlined text-secondary text-sm">check_circle</span> Community support</li>
                <li className="flex items-center gap-3 opacity-30"><span className="material-symbols-outlined text-sm">cancel</span> Enterprise security (SSO)</li>
              </ul>
              <button className="w-full border border-outline-variant/50 hover:bg-surface-container-low text-on-surface font-bold py-3 rounded-sm transition-all">Get Started Free</button>
            </div>
            <div className="relative bg-surface border-2 border-primary p-10 rounded-xl flex flex-col items-center text-center shadow-xl shadow-primary/5">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-primary px-4 py-1 rounded-full text-[10px] font-bold text-on-primary tracking-widest uppercase">Most Popular</div>
              <span className="px-4 py-1 rounded-full bg-primary/10 text-label-sm font-label-sm text-primary mb-6">ENTERPRISE</span>
              <h3 className="font-headline-md text-headline-md mb-2">Commercial</h3>
              <div className="mb-8">
                <span className="text-4xl font-bold">Custom</span>
              </div>
              <ul className="space-y-4 mb-10 text-on-surface-variant text-left w-full">
                <li className="flex items-center gap-3"><span className="material-symbols-outlined text-primary text-sm">check_circle</span> Advanced RBAC & SSO</li>
                <li className="flex items-center gap-3"><span className="material-symbols-outlined text-primary text-sm">check_circle</span> Private Cloud Deployment</li>
                <li className="flex items-center gap-3"><span className="material-symbols-outlined text-primary text-sm">check_circle</span> Hardware-Aware Scaling</li>
                <li className="flex items-center gap-3"><span className="material-symbols-outlined text-primary text-sm">check_circle</span> 24/7 Priority SLA</li>
              </ul>
              <button className="w-full bg-primary text-on-primary font-bold py-3 rounded-sm hover:opacity-90 transition-all underglow-primary">Contact Sales</button>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-surface-container-lowest py-stack-lg border-t border-outline-variant/20 px-margin-mobile md:px-margin-desktop">
        <div className="max-w-container-max mx-auto flex flex-col md:flex-row justify-between items-start gap-stack-lg">
          <div className="max-w-xs">
            <div className="flex items-center gap-stack-md mb-4">
              <img alt="AgenticRAG Logo" className="h-8 w-8 object-contain" src="https://lh3.googleusercontent.com/aida-public/AB6AXuBcYWF4-dmV6XSJxVTyCELz38bBICSIVxuIHFaNSWtqhB7oFxd0YOhR14j9KISWPb7ymD_v0AwD1nWU0OGPo-Bp2Vbk7i3-KgvSrNfyVOiFBQ4gBOkFazRBNPfHRxx2nPc5UK9PdAhYOqtRwuAKdkDfekYqg2aBggnCXheXqavp5caEwSMGxnx-rLg5yYNDJzb8W5Wti_9a4aQyFVB7jmYNxN8posh1QyD6AINH0CuQY6H_80I9EIyTdGwzZt40IcpeXFIi7PeAig"/>
              <span className="font-display-lg text-headline-md font-bold text-on-surface">AgenticRAG</span>
            </div>
            <p className="text-on-surface-variant text-body-md mb-6">The enterprise-ready Retrieval-Augmented Generation framework for mission-critical AI agents.</p>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-stack-lg">
            <div className="flex flex-col gap-4">
              <span className="text-on-surface font-bold text-label-sm uppercase tracking-widest">Platform</span>
              <a className="text-on-surface-variant hover:text-primary text-body-md transition-colors" href="#">Solutions</a>
              <a className="text-on-surface-variant hover:text-primary text-body-md transition-colors" href="#">Features</a>
              <a className="text-on-surface-variant hover:text-primary text-body-md transition-colors" href="#">Documentation</a>
            </div>
            <div className="flex flex-col gap-4">
              <span className="text-on-surface font-bold text-label-sm uppercase tracking-widest">Company</span>
              <a className="text-on-surface-variant hover:text-primary text-body-md transition-colors" href="#">About Us</a>
              <a className="text-on-surface-variant hover:text-primary text-body-md transition-colors" href="#">Blog</a>
              <a className="text-on-surface-variant hover:text-primary text-body-md transition-colors" href="#">Careers</a>
            </div>
            <div className="flex flex-col gap-4">
              <span className="text-on-surface font-bold text-label-sm uppercase tracking-widest">Legal</span>
              <a className="text-on-surface-variant hover:text-primary text-body-md transition-colors" href="#">Privacy Policy</a>
              <a className="text-on-surface-variant hover:text-primary text-body-md transition-colors" href="#">Terms of Service</a>
              <a className="text-on-surface-variant hover:text-primary text-body-md transition-colors" href="#">Security</a>
            </div>
          </div>
        </div>
        <div className="max-w-container-max mx-auto mt-20 pt-8 border-t border-outline-variant/10 text-center md:text-left">
          <p className="text-on-surface-variant font-label-sm text-label-sm">© 2026 AgenticRAG Enterprise. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}

export default App;
