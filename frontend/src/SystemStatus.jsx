import React, { useState, useEffect } from 'react';

function SystemStatus() {
  const [status, setStatus] = useState(null);
  const [llmConfig, setLlmConfig] = useState({ master_agent: '', department_agent: '', temperature: 0.0 });
  const [availableModels, setAvailableModels] = useState([]);
  const username = localStorage.getItem('username');

  useEffect(() => {
    fetchStatus();
    fetchLlmConfig();
    fetchAvailableModels();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/admin/system/status`, { headers: { 'x-username': username } });
      const data = await res.json();
      setStatus(data);
    } catch (e) {
      console.error("Failed to fetch system status", e);
    }
  };

  const fetchLlmConfig = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/admin/llm/config`, { headers: { 'x-username': username } });
      const data = await res.json();
      setLlmConfig(data);
    } catch (e) {
      console.error("Failed to fetch LLM config", e);
    }
  };

  const fetchAvailableModels = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/admin/llm/available`, { headers: { 'x-username': username } });
      const data = await res.json();
      setAvailableModels(data.models || []);
    } catch (e) {
      console.error("Failed to fetch models", e);
    }
  };

  const updateLlmConfig = async (newConfig) => {
    setLlmConfig(newConfig);
    try {
      await fetch(`http://127.0.0.1:8000/admin/llm/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'x-username': username },
        body: JSON.stringify(newConfig)
      });
    } catch (e) {
      alert("Failed to update LLM configuration");
    }
  };

  const clearCache = async () => {
    if (!window.confirm("Are you sure you want to clear the entity cache? This may cause a temporary slowdown.")) return;
    try {
      await fetch(`http://127.0.0.1:8000/admin/system/cache/clear`, {
        method: 'POST',
        headers: { 'x-username': username }
      });
      alert("Cache cleared successfully!");
    } catch (e) {
      alert("Failed to clear cache");
    }
  };

  if (!status) return <div className="p-6 text-center text-on-surface-variant">Loading System Status...</div>;

  return (
    <div className="bg-white rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden h-full flex flex-col">
      <div className="p-4 border-b border-outline-variant/20 bg-surface-container-lowest">
        <h2 className="font-headline-md text-lg text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">monitoring</span>
          System Status
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        
        {/* Hardware Card */}
        <div className="bg-surface-container-lowest border border-outline-variant/20 rounded-lg p-4">
          <h3 className="text-sm font-bold text-on-surface-variant uppercase tracking-wider mb-3">Hardware</h3>
          <div className="space-y-3 text-sm">
            <div>
              <div className="flex justify-between mb-1">
                <span>CPU Usage</span>
                <span className="font-bold">{status.hardware.cpu}%</span>
              </div>
              <div className="w-full bg-surface-container-high rounded-full h-2">
                <div className="bg-primary h-2 rounded-full" style={{ width: `${status.hardware.cpu}%` }}></div>
              </div>
            </div>
            <div>
              <div className="flex justify-between mb-1">
                <span>RAM Usage ({status.hardware.ram_used_gb.toFixed(1)} / {status.hardware.ram_total_gb.toFixed(1)} GB)</span>
                <span className="font-bold">{status.hardware.ram_percent}%</span>
              </div>
              <div className="w-full bg-surface-container-high rounded-full h-2">
                <div className="bg-primary h-2 rounded-full" style={{ width: `${status.hardware.ram_percent}%` }}></div>
              </div>
            </div>
            {status.hardware.gpus.map((gpu, i) => (
              <div key={i}>
                <div className="flex justify-between mb-1">
                  <span className="truncate w-32" title={gpu.name}>{gpu.name}</span>
                  <span className="font-bold">{gpu.load.toFixed(1)}% Load</span>
                </div>
                <div className="w-full bg-surface-container-high rounded-full h-2">
                  <div className="bg-primary h-2 rounded-full" style={{ width: `${gpu.load}%` }}></div>
                </div>
                <div className="text-xs text-on-surface-variant mt-1 text-right">
                  VRAM: {(gpu.memoryUsed).toFixed(0)}MB / {(gpu.memoryTotal).toFixed(0)}MB
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Background Tasks */}
        <div className="bg-surface-container-lowest border border-outline-variant/20 rounded-lg p-4">
          <h3 className="text-sm font-bold text-on-surface-variant uppercase tracking-wider mb-3">Background Tasks</h3>
          <div className="space-y-3 text-sm">
            {Object.keys(status.background_tasks || {}).length === 0 ? (
              <p className="text-on-surface-variant italic">No active tasks</p>
            ) : (
              Object.entries(status.background_tasks).map(([id, task]) => (
                <div key={id} className="border-b border-outline-variant/10 pb-2 last:border-0 last:pb-0">
                  <div className="flex justify-between mb-1">
                    <span className="font-medium truncate">{task.task}</span>
                    <span className={`font-bold ${task.status === 'error' ? 'text-error' : task.status === 'completed' ? 'text-success' : 'text-primary'}`}>
                      {task.status === 'running' ? `${Math.round((task.progress / task.total) * 100)}%` : task.status}
                    </span>
                  </div>
                  {task.status === 'running' && (
                    <div className="w-full bg-surface-container-high rounded-full h-1.5 mt-1">
                      <div className="bg-primary h-1.5 rounded-full transition-all" style={{ width: `${(task.progress / task.total) * 100}%` }}></div>
                    </div>
                  )}
                  {task.error && <p className="text-xs text-error mt-1">{task.error}</p>}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Storage */}
        <div className="bg-surface-container-lowest border border-outline-variant/20 rounded-lg p-4">
          <h3 className="text-sm font-bold text-on-surface-variant uppercase tracking-wider mb-3">Storage & Cache</h3>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>Vector DB Size</span>
              <span className="font-mono bg-surface-container px-2 py-0.5 rounded">{status.storage.vector_db_mb.toFixed(1)} MB</span>
            </div>
            <div className="flex justify-between">
              <span>KG SQLite Size</span>
              <span className="font-mono bg-surface-container px-2 py-0.5 rounded">{status.storage.kg_db_mb.toFixed(1)} MB</span>
            </div>
            <div className="flex justify-between">
              <span>Raw Uploads</span>
              <span className="font-mono bg-surface-container px-2 py-0.5 rounded">{status.storage.uploads_mb.toFixed(1)} MB</span>
            </div>
          </div>
          <button 
            onClick={clearCache}
            className="mt-4 w-full bg-error-container text-on-error-container hover:bg-error hover:text-white py-2 rounded-lg text-sm font-bold transition-colors"
          >
            Clear Entity Cache
          </button>
        </div>

        {/* LLM Config */}
        <div className="bg-surface-container-lowest border border-outline-variant/20 rounded-lg p-4">
          <h3 className="text-sm font-bold text-on-surface-variant uppercase tracking-wider mb-3">LLM Configuration</h3>
          <div className="space-y-4 text-sm">
            <div>
              <label className="block mb-1 font-medium">Master Agent Model</label>
              <select 
                value={llmConfig.master_agent} 
                onChange={(e) => updateLlmConfig({...llmConfig, master_agent: e.target.value})}
                className="w-full border border-outline-variant/40 rounded-lg px-3 py-2 bg-white focus:ring-1 focus:ring-primary focus:outline-none"
              >
                {availableModels.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="block mb-1 font-medium">Department Model</label>
              <select 
                value={llmConfig.department_agent} 
                onChange={(e) => updateLlmConfig({...llmConfig, department_agent: e.target.value})}
                className="w-full border border-outline-variant/40 rounded-lg px-3 py-2 bg-white focus:ring-1 focus:ring-primary focus:outline-none"
              >
                {availableModels.map(m => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className="flex justify-between mb-1 font-medium">
                <span>Temperature</span>
                <span>{llmConfig.temperature.toFixed(1)}</span>
              </label>
              <input 
                type="range" 
                min="0" max="1" step="0.1" 
                value={llmConfig.temperature}
                onChange={(e) => updateLlmConfig({...llmConfig, temperature: parseFloat(e.target.value)})}
                className="w-full"
              />
              <p className="text-xs text-on-surface-variant mt-1">Lower is more precise, higher is more creative.</p>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

export default SystemStatus;
