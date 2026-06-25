import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ToolChip from './ToolChip';
import DiffCard from './DiffCard';

function bubbleClass(role) {
  if (role === 'user') return 'bg-primary text-primary-fg';
  if (role === 'error') return 'bg-error-bg border border-error text-error';
  return 'bg-surface border border-border text-text';
}

export default function ChatPane({ transcript, proposal, sending, onSend, onApply, onReject, onCancel }) {
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
            <div className={`inline-block max-w-[80%] p-3 rounded-2xl text-sm ${bubbleClass(m.role)} ${m.role === 'user' || m.role === 'error' ? 'whitespace-pre-wrap' : 'prose prose-sm max-w-none prose-pre:bg-surface-muted prose-pre:text-text'}`}>
              {m.role === 'user' || m.role === 'error'
                ? m.text
                : <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.text || ''}</ReactMarkdown>}
            </div>
          </div>
        ))}
        {sending && (
          <div className="text-left" data-testid="thinking">
            <span className="inline-block p-3 rounded-2xl text-sm bg-surface border border-border text-text-tertiary">thinking…</span>
          </div>
        )}
        {proposal && <DiffCard proposal={proposal} onApply={onApply} onReject={onReject} />}
      </div>
      <form onSubmit={submit} data-testid="chat-form" className="p-4 border-t border-border bg-surface">
        <div className="flex gap-2">
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about or edit the dialogue…"
            className="flex-1 border border-border rounded-xl px-3 py-2 text-sm text-text bg-surface focus:outline-none focus:ring-2 focus:ring-primary" />
          {sending
            ? <button type="button" onClick={onCancel} className="px-4 bg-error text-primary-fg rounded-xl hover:bg-red-700">Stop</button>
            : <button type="submit" className="px-4 bg-primary text-primary-fg rounded-xl hover:bg-primary-hover">Send</button>}
        </div>
      </form>
    </div>
  );
}
