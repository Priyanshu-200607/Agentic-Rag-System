import React, { useState, useEffect, useRef } from 'react';

function LogViewer() {
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState('all'); // all, query, task, system
  const username = localStorage.getItem('username');
  
  const endRef = useRef(null);
  const scrollContainerRef = useRef(null);
  const [isAutoScroll, setIsAutoScroll] = useState(true);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 3000);
    return () => clearInterval(interval);
  }, [activeTab]);

  useEffect(() => {
    if (isAutoScroll && endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, isAutoScroll]);

  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    // If user is within 50px of bottom, auto scroll is enabled
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
    setIsAutoScroll(isAtBottom);
  };

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
    if (line.includes('[ERROR]') || line.includes('Failed') || line.includes('Error')) return 'text-red-400 font-bold';
    if (line.includes('[WARNING]')) return 'text-yellow-400 font-bold';
    if (line.includes('[QUERY]')) return 'text-green-400';
    if (line.includes('[TASK]')) return 'text-blue-400';
    if (line.includes('[SYSTEM]')) return 'text-gray-400';
    return 'text-gray-200';
  };

  return (
    <div className="flex flex-col h-full p-4 space-y-4">
      {/* Header - Fixed Height */}
      <div className="flex items-center justify-between shrink-0">
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
      
      {/* Logs Container - Flexible Height & Scrollable */}
      <div 
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="bg-black/95 rounded-xl p-4 flex-1 overflow-y-auto font-mono text-sm shadow-inner min-h-0"
      >
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
