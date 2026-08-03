import React, { useState, useEffect, useRef } from 'react';
import Layout from './Layout';

function Chat() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [thinkingStatus, setThinkingStatus] = useState('');
  
  const username = localStorage.getItem('username');
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, thinkingStatus]);

  const loadSessions = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/chat/sessions?username=${username}`);
      const data = await res.json();
      setSessions(data);
      
      const savedSession = localStorage.getItem('activeSessionId');
      if (savedSession && data.find(s => s.id === savedSession)) {
        loadSessionMessages(savedSession);
      } else {
        startNewChat();
      }
    } catch (e) {
      console.error(e);
      startNewChat();
    }
  };

  const loadSessionMessages = async (sid) => {
    setActiveSessionId(sid);
    localStorage.setItem('activeSessionId', sid);
    try {
      const res = await fetch(`http://127.0.0.1:8000/chat/session/${sid}?username=${username}`);
      const data = await res.json();
      setMessages(data);
    } catch (e) {
      setMessages([]);
    }
  };

  const startNewChat = async () => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/chat/session?username=${username}`, { method: 'POST' });
      const data = await res.json();
      setActiveSessionId(data.session_id);
      localStorage.setItem('activeSessionId', data.session_id);
      setMessages([]);
      loadSessions();
    } catch (e) {
      console.error(e);
    }
  };

  const handleSend = async () => {
    if (!question.trim() || isProcessing) return;

    const newMessages = [...messages, { sender: 'You', text: question }];
    setMessages(newMessages);
    const currentQuestion = question;
    setQuestion('');
    setIsProcessing(true);
    setThinkingStatus('Initializing request...');

    try {
      const response = await fetch(`http://127.0.0.1:8000/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: currentQuestion, username, session_id: activeSessionId })
      });

      if (!response.ok) throw new Error('Failed to connect to server');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let finalAnswer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep the incomplete line in the buffer

        for (const line of lines) {
          if (line.trim()) {
            const data = JSON.parse(line);
            if (data.type === 'status') {
              setThinkingStatus(data.message);
            } else if (data.type === 'answer') {
              finalAnswer = data.message;
            }
          }
        }
      }
      
      setMessages([...newMessages, { sender: 'Assistant', text: finalAnswer }]);
      
      // Update session list in case it's a new session getting its first message
      if (newMessages.length === 1) loadSessions();

    } catch (e) {
      setMessages([...newMessages, { sender: 'System', text: 'Error: Failed to process request.' }]);
    } finally {
      setIsProcessing(false);
      setThinkingStatus('');
    }
  };

  return (
    <Layout activeTab="chat">
      <div className="max-w-7xl mx-auto flex gap-6 h-[calc(100vh-140px)]">
        
        {/* Sidebar for Sessions */}
        <div className="w-64 bg-white rounded-xl shadow-sm border border-outline-variant/30 flex flex-col hidden md:flex shrink-0">
          <div className="p-4 border-b border-outline-variant/20">
            <button 
              onClick={startNewChat}
              className="w-full bg-primary text-white px-4 py-2 rounded-lg text-sm font-bold flex items-center justify-center gap-2 hover:opacity-90"
            >
              <span className="material-symbols-outlined text-lg">add</span>
              New Chat
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {sessions.map(s => (
              <button 
                key={s.id}
                onClick={() => loadSessionMessages(s.id)}
                className={`w-full text-left px-4 py-3 rounded-lg text-sm truncate flex flex-col ${activeSessionId === s.id ? 'bg-primary-container text-on-primary-container font-bold' : 'hover:bg-surface-container-low text-on-surface'}`}
              >
                <span>Session {s.id.slice(0, 6)}</span>
                <span className="text-xs opacity-70">{s.messages_count} messages</span>
              </button>
            ))}
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 bg-white rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden flex flex-col h-full">
          {/* Header */}
          <div className="p-6 border-b border-outline-variant/20 flex items-center gap-3 shrink-0">
            <span className="material-symbols-outlined text-primary text-3xl">chat</span>
            <h1 className="text-headline-md font-headline-md text-on-surface">Assistant Chat</h1>
          </div>
          
          {/* Messages */}
          <div className="flex-1 p-6 overflow-y-auto bg-surface-container-lowest/50 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-on-surface-variant py-10">
                <span className="material-symbols-outlined text-4xl mb-2 opacity-50">forum</span>
                <p>Hello! How can I help you today?</p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.sender === 'You' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${msg.sender === 'You' ? 'bg-primary text-white' : msg.sender === 'System' ? 'bg-error-container text-on-error-container' : 'bg-surface-container border border-outline-variant/20 text-on-surface'} shadow-sm`}>
                    <p className="font-body-md text-sm whitespace-pre-wrap">{msg.text}</p>
                  </div>
                </div>
              ))
            )}
            
            {/* Thinking Status */}
            {isProcessing && (
              <div className="flex justify-start">
                <div className="max-w-[80%] rounded-2xl px-5 py-3 bg-surface-container border border-outline-variant/20 shadow-sm flex items-center gap-3">
                  <div className="animate-spin w-4 h-4 border-2 border-primary border-t-transparent rounded-full"></div>
                  <p className="font-body-md text-sm text-on-surface-variant italic">{thinkingStatus}</p>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          
          {/* Input */}
          <div className="p-4 border-t border-outline-variant/20 bg-white shrink-0">
            <div className="flex gap-3">
              <input 
                type="text" 
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder={isProcessing ? "Waiting for response..." : "Ask a question..."}
                disabled={isProcessing}
                className="flex-1 bg-surface-container-low border border-outline-variant/40 rounded-full px-6 py-3 text-sm focus:ring-2 focus:ring-primary/20 focus:outline-none focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button 
                onClick={handleSend}
                disabled={isProcessing || !question.trim()}
                className="bg-primary text-white h-12 w-12 rounded-full flex items-center justify-center hover:opacity-90 transition-opacity shadow-sm shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <span className="material-symbols-outlined" style={{fontVariationSettings: "'FILL' 1"}}>send</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

export default Chat;
