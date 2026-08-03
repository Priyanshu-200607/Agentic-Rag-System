import React, { useState, useEffect, useRef } from 'react';

function LogViewer() {
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState('all'); // all, query, task, system
  const username = localStorage.getItem('username');
  const endRef = useRef(null);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, [activeTab]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  const fetchLogs = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/admin/logs?type=${activeTab}&lines=100`, { 
        headers: { 'x-username': username } 
      });
      const data = await res.json();
      setLogs(data.logs || []);
    } catch (e) {
      console.error("Failed to fetch logs", e);
    }
  };

  const getLogColor = (line) => {
    if (line.includes('[ERROR]') || line.includes('Failed') || line.includes('Error')) return 'text-error';
    if (line.includes('[WARNING]')) return 'text-warning';
    if (line.includes('[QUERY]')) return 'text-tertiary';
    if (line.includes('[TASK]')) return 'text-primary';
    if (line.includes('[SYSTEM]')) return 'text-on-surface-variant';
    return 'text-on-surface';
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-headline-md text-lg text-on-surface flex items-center gap-2">
          <span className="material-symbols-outlined text-primary">terminal</span>
          Unified Log Viewer
        </h2>
        <div className="flex bg-surface-container-low rounded-lg p-1 gap-1">
          {['all', 'query', 'task', 'system'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-md text-xs font-bold capitalize transition-colors ${activeTab === tab ? 'bg-primary text-white' : 'text-on-surface-variant hover:bg-surface-container-high'}`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>
      
      <div className="bg-[#1e1e1e] rounded-xl p-4 h-64 overflow-y-auto font-mono text-xs shadow-inner">
        {logs.length === 0 ? (
          <div className="text-on-surface-variant/50 italic text-center mt-10">No logs available for this filter...</div>
        ) : (
          logs.map((line, idx) => (
            <div key={idx} className={`mb-1 whitespace-pre-wrap ${getLogColor(line)}`}>
              {line}
            </div>
          ))
        )}
        <div ref={endRef} />
      </div>
    </div>
  );
}

export default LogViewer;
