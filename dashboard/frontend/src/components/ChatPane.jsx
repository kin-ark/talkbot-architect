import React, { useState } from 'react';
import ToolChip from './ToolChip';
import DiffCard from './DiffCard';

export default function ChatPane({ transcript, proposal, onSend, onApply, onReject }) {
  const [input, setInput] = useState('');
  const submit = (e) => { e.preventDefault(); if (!input.trim()) return; onSend(input.trim()); setInput(''); };
  return (
    <div className="flex flex-col h-full" data-testid="chat-pane">
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {transcript.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'text-right' : 'text-left'}>
            {m.tool_trace?.length > 0 && (
              <div className="mb-1">{m.tool_trace.map((t, j) => <ToolChip key={j} name={t.name} args={t.arguments} />)}</div>
            )}
            <div className={`inline-block max-w-[80%] p-3 rounded-2xl text-sm whitespace-pre-wrap ${m.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-white border border-slate-200 text-slate-700'}`}>{m.text}</div>
          </div>
        ))}
        {proposal && <DiffCard proposal={proposal} onApply={onApply} onReject={onReject} />}
      </div>
      <form onSubmit={submit} data-testid="chat-form" className="p-4 border-t border-slate-200 bg-white">
        <div className="flex gap-2">
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about or edit the dialogue…"
            className="flex-1 border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500" />
          <button type="submit" className="px-4 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700">Send</button>
        </div>
      </form>
    </div>
  );
}
