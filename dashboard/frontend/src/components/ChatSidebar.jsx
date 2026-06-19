import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Sparkles } from 'lucide-react';
import axios from 'axios';

export default function ChatSidebar({ analysisContext }) {
  const [messages, setMessages] = useState([
    { 
      role: 'agent', 
      text: 'Hello! I am your Talkbot Architect Assistant. Upload a dialogue JSON file to start the audit, or ask me any questions about speech components, canvas structure, variables, or intents.' 
    }
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputValue.trim()) return;

    const userMessage = inputValue.trim();
    setInputValue('');
    setMessages(prev => [...prev, { role: 'user', text: userMessage }]);
    setIsTyping(true);

    try {
      // Build context for the agent
      const context = analysisContext 
        ? {
            errors: analysisContext.summary?.errors || 0,
            warnings: analysisContext.summary?.warnings || 0,
            findings: analysisContext.findings || []
          }
        : {};

      const response = await axios.post('http://localhost:8000/chat', {
        message: userMessage,
        context: context
      });

      setMessages(prev => [...prev, { role: 'agent', text: response.data.response }]);
    } catch (err) {
      console.error('Chat request failed:', err);
      setMessages(prev => [
        ...prev, 
        { 
          role: 'agent', 
          text: 'Sorry, I encountered an error communicating with the agent server. Please make sure the backend is running.' 
        }
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="w-96 border-l border-gray-200 bg-slate-50 flex flex-col h-full shadow-2xl relative">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 bg-white flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-md">
            <Bot size={18} />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-gray-800 flex items-center gap-1.5">
              AI Auditor Assistant
              <Sparkles size={12} className="text-indigo-500 animate-pulse" />
            </h2>
            <p className="text-[10px] text-gray-400 font-medium">Talkbot Architect v1.0</p>
          </div>
        </div>
      </div>

      {/* Message Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((m, i) => {
          const isUser = m.role === 'user';
          return (
            <div key={i} className={`flex gap-2.5 ${isUser ? 'justify-end' : 'justify-start'}`}>
              {!isUser && (
                <div className="h-7 w-7 rounded-md bg-indigo-100 flex items-center justify-center text-indigo-600 self-end shadow-sm">
                  <Bot size={14} />
                </div>
              )}
              <div 
                className={`max-w-[80%] p-3 rounded-2xl text-sm leading-relaxed shadow-sm transition-all hover:shadow-md ${
                  isUser 
                    ? 'bg-indigo-600 text-white rounded-br-none' 
                    : 'bg-white border border-gray-200 text-gray-700 rounded-bl-none'
                }`}
              >
                <p className="whitespace-pre-wrap">{m.text}</p>
              </div>
              {isUser && (
                <div className="h-7 w-7 rounded-md bg-indigo-600 flex items-center justify-center text-white self-end shadow-sm">
                  <User size={14} />
                </div>
              )}
            </div>
          );
        })}

        {isTyping && (
          <div className="flex gap-2.5 justify-start">
            <div className="h-7 w-7 rounded-md bg-indigo-100 flex items-center justify-center text-indigo-600 self-end shadow-sm">
              <Bot size={14} />
            </div>
            <div className="bg-white border border-gray-200 p-3 rounded-2xl rounded-bl-none flex items-center gap-1 shadow-sm">
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
              <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={handleSend} className="p-4 border-t border-gray-200 bg-white shadow-inner">
        <div className="flex gap-2">
          <input 
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Ask about findings or optimization..." 
            className="flex-1 border border-gray-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all shadow-inner"
          />
          <button 
            type="submit" 
            className="p-2 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 active:scale-95 transition-all shadow-md flex items-center justify-center"
          >
            <Send size={16} />
          </button>
        </div>
      </form>
    </div>
  );
}
