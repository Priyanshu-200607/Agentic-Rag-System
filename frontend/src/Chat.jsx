import React, { useState } from 'react';
import Layout from './Layout';

function Chat() {
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const username = localStorage.getItem('username');

  const handleSend = async () => {
    if (!question.trim()) return;

    const newMessages = [...messages, { sender: 'You', text: question }];
    setMessages(newMessages);
    setQuestion('');

    try {
      const response = await fetch(`http://127.0.0.1:8000/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, username })
      });

      const data = await response.json();
      setMessages([...newMessages, { sender: 'Assistant', text: data.answer }]);
    } catch (e) {
      setMessages([...newMessages, { sender: 'System', text: 'Error: Failed to connect to server.' }]);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <Layout activeTab="chat">
      <div className="max-w-4xl mx-auto space-y-stack-lg flex flex-col h-[calc(100vh-140px)]">
        <div className="bg-white rounded-xl shadow-sm border border-outline-variant/30 overflow-hidden flex flex-col h-full">
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
                    <p className="font-body-md text-sm">{msg.text}</p>
                  </div>
                </div>
              ))
            )}
          </div>
          
          {/* Input */}
          <div className="p-4 border-t border-outline-variant/20 bg-white shrink-0">
            <div className="flex gap-3">
              <input 
                type="text" 
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question..."
                className="flex-1 bg-surface-container-low border border-outline-variant/40 rounded-full px-6 py-3 text-sm focus:ring-2 focus:ring-primary/20 focus:outline-none focus:border-primary"
              />
              <button 
                onClick={handleSend}
                className="bg-primary text-white h-12 w-12 rounded-full flex items-center justify-center hover:opacity-90 transition-opacity shadow-sm shrink-0"
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
